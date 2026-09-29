import asyncio
from pathlib import Path
from urllib.parse import parse_qs

import httpx
import pytest

from app.adapters.publishing.base import PublishRequest, PublishResult
from app.adapters.publishing.instagram import InstagramPublishAdapter, InstagramPublishError
from app.core.enums import PublishStatus
from app.core.security import encrypt_secret
from app.db.init_db import _seed_publish_platforms
from app.models import PublishAccount, PublishPlatform, PublishTask
from app.schemas.publishing import PublishTaskOut
from app.tasks.publish_tasks import run_publish_task


ACCESS_TOKEN = "instagram-super-secret-token"
IG_USER_ID = "17890000000000000"


class FakeClock:
    def __init__(self) -> None:
        self.value = 0.0

    def __call__(self) -> float:
        return self.value

    async def sleep(self, seconds: float) -> None:
        self.value += seconds


class CapturingLogger:
    def __init__(self) -> None:
        self.entries: list[tuple[str, str, dict]] = []

    def info(self, event: str, **values) -> None:
        self.entries.append(("info", event, values))

    def warning(self, event: str, **values) -> None:
        self.entries.append(("warning", event, values))


def make_instagram_adapter(
    handler,
    *,
    processing_timeout_seconds: float = 10,
    poll_interval_seconds: float = 1,
    clock: FakeClock | None = None,
) -> InstagramPublishAdapter:
    platform = PublishPlatform(
        name="Instagram",
        code="instagram",
        adapter_type="instagram_graph",
        api_base_url="https://graph.instagram.com",
        api_version="v26.0",
        auth_type="oauth2",
        capabilities={"supports_video": True, "supports_reel": True},
        extra_config={
            "poll_interval_seconds": poll_interval_seconds,
            "processing_timeout_seconds": processing_timeout_seconds,
            "http_timeout_seconds": 3,
            "require_https_video_url": True,
        },
        enabled=True,
    )
    account = PublishAccount(
        platform_id=platform.id,
        name="Instagram test account",
        account_identifier="creator.name",
        ig_user_id=IG_USER_ID,
        access_token_encrypted=encrypt_secret(ACCESS_TOKEN),
        extra_config={},
        enabled=True,
    )
    selected_clock = clock or FakeClock()
    return InstagramPublishAdapter(
        platform,
        account,
        transport=httpx.MockTransport(handler),
        sleep=selected_clock.sleep,
        monotonic=selected_clock,
    )


def publish_request(
    *,
    video_url: str | None = "https://cdn.example.com/reel.mp4",
    caption: str | None = "Instagram API PoC",
    publish_type: str = "reel",
) -> PublishRequest:
    platform_payload = {}
    if video_url is not None:
        platform_payload["video_url"] = video_url
    if caption is not None:
        platform_payload["caption"] = caption
    return PublishRequest(
        video_path=Path("unused-local-file.mp4"),
        title="Reel",
        content="Common content",
        description="Common description",
        tags=[],
        publish_type=publish_type,
        common_payload={},
        platform_payload=platform_payload,
        overrides={},
        idempotency_key="instagram-test-request",
    )


def form_values(request: httpx.Request) -> dict[str, list[str]]:
    return parse_qs(request.content.decode("utf-8"), keep_blank_values=True)


def test_create_media_container_returns_container_id_and_reel_payload():
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"id": "container_123"})

    adapter = make_instagram_adapter(handler)
    payload = adapter.build_platform_payload(publish_request(publish_type="video"))

    async def create() -> str:
        async with httpx.AsyncClient(transport=adapter._transport) as client:
            return await adapter.create_media_container(client, payload)

    assert asyncio.run(create()) == "container_123"
    assert len(seen) == 1
    assert seen[0].method == "POST"
    assert seen[0].url.path == f"/v26.0/{IG_USER_ID}/media"
    assert form_values(seen[0]) == {
        "media_type": ["REELS"],
        "video_url": ["https://cdn.example.com/reel.mp4"],
        "caption": ["Instagram API PoC"],
        "share_to_feed": ["true"],
        "access_token": [ACCESS_TOKEN],
    }


def test_publish_waits_for_finished_then_returns_distinct_media_id():
    calls: list[str] = []
    status_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal status_count
        calls.append(f"{request.method} {request.url.path}")
        if request.url.path.endswith(f"/{IG_USER_ID}/media"):
            return httpx.Response(200, json={"id": "container_123"})
        if request.url.path.endswith("/container_123"):
            status_count += 1
            status = "IN_PROGRESS" if status_count == 1 else "FINISHED"
            return httpx.Response(200, json={"id": "container_123", "status_code": status})
        if request.url.path.endswith(f"/{IG_USER_ID}/media_publish"):
            assert form_values(request)["creation_id"] == ["container_123"]
            return httpx.Response(200, json={"id": "media_456"})
        if request.url.path.endswith("/media_456"):
            assert request.url.params["fields"] == "permalink,username"
            return httpx.Response(
                200,
                json={
                    "permalink": "https://www.instagram.com/reel/ABC123/",
                    "username": "published.creator",
                },
            )
        raise AssertionError(f"Unexpected request: {request.method} {request.url}")

    result = asyncio.run(make_instagram_adapter(handler).publish_video(publish_request()))

    assert calls == [
        f"POST /v26.0/{IG_USER_ID}/media",
        "GET /v26.0/container_123",
        "GET /v26.0/container_123",
        f"POST /v26.0/{IG_USER_ID}/media_publish",
        "GET /v26.0/media_456",
    ]
    assert result.status == "success"
    assert result.provider_container_id == "container_123"
    assert result.platform_post_id == "media_456"
    assert result.publish_url == "https://www.instagram.com/p/ABC123/"
    assert result.platform_url == "https://www.instagram.com/published.creator/"
    assert result.metadata == {
        "container_id": "container_123",
        "media_id": "media_456",
        "permalink": "https://www.instagram.com/reel/ABC123/",
        "username": "published.creator",
    }


def test_publish_does_not_treat_numeric_media_id_as_permalink_shortcode():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith(f"/{IG_USER_ID}/media"):
            return httpx.Response(200, json={"id": "container_without_permalink"})
        if request.url.path.endswith("/container_without_permalink"):
            return httpx.Response(200, json={"status_code": "FINISHED"})
        if request.url.path.endswith(f"/{IG_USER_ID}/media_publish"):
            return httpx.Response(200, json={"id": "18180224632437876"})
        if request.url.path.endswith("/18180224632437876"):
            return httpx.Response(200, json={"id": "18180224632437876"})
        raise AssertionError(f"Unexpected request: {request.method} {request.url}")

    result = asyncio.run(make_instagram_adapter(handler).publish_video(publish_request()))

    assert result.platform_post_id == "18180224632437876"
    assert result.publish_url is None


def test_processing_timeout_does_not_call_media_publish():
    clock = FakeClock()
    publish_calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal publish_calls
        if request.url.path.endswith(f"/{IG_USER_ID}/media"):
            return httpx.Response(200, json={"id": "container_timeout"})
        if request.url.path.endswith("/container_timeout"):
            return httpx.Response(200, json={"status_code": "IN_PROGRESS"})
        if request.url.path.endswith("/media_publish"):
            publish_calls += 1
        return httpx.Response(500)

    adapter = make_instagram_adapter(
        handler,
        processing_timeout_seconds=2,
        poll_interval_seconds=1,
        clock=clock,
    )
    with pytest.raises(InstagramPublishError) as exc_info:
        asyncio.run(adapter.publish_video(publish_request()))

    assert exc_info.value.error_code == "PROCESSING_TIMEOUT"
    assert exc_info.value.stage == "WAIT_CONTAINER"
    assert exc_info.value.container_id == "container_timeout"
    assert publish_calls == 0


def test_container_status_5xx_is_retried_within_processing_timeout():
    status_calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal status_calls
        if request.url.path.endswith(f"/{IG_USER_ID}/media"):
            return httpx.Response(200, json={"id": "container_retry"})
        if request.url.path.endswith("/container_retry"):
            status_calls += 1
            if status_calls == 1:
                return httpx.Response(503, json={"error": {"message": "temporary"}})
            return httpx.Response(200, json={"status_code": "FINISHED"})
        return httpx.Response(200, json={"id": "media_after_retry"})

    result = asyncio.run(make_instagram_adapter(handler).publish_video(publish_request()))

    assert status_calls == 2
    assert result.platform_post_id == "media_after_retry"


def test_container_creation_meta_error_is_structured_and_publish_is_not_called():
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        return httpx.Response(
            400,
            json={
                "error": {
                    "message": "Unsupported post request",
                    "type": "GraphMethodException",
                    "code": 100,
                    "error_subcode": 33,
                    "fbtrace_id": "trace-123",
                }
            },
        )

    with pytest.raises(InstagramPublishError) as exc_info:
        asyncio.run(make_instagram_adapter(handler).publish_video(publish_request()))

    error = exc_info.value
    assert calls == [f"/v26.0/{IG_USER_ID}/media"]
    assert error.error_code == "INSTAGRAM_CREATE_CONTAINER_FAILED"
    assert error.stage == "CREATE_CONTAINER"
    assert error.http_status == 400
    assert error.meta_error_type == "GraphMethodException"
    assert error.meta_error_code == 100
    assert error.meta_error_subcode == 33
    assert error.fbtrace_id == "trace-123"


def test_missing_video_url_fails_before_calling_instagram():
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError(f"Instagram must not be called: {request.url}")

    with pytest.raises(InstagramPublishError) as exc_info:
        asyncio.run(
            make_instagram_adapter(handler).publish_video(
                publish_request(video_url=None),
            )
        )

    assert exc_info.value.error_code == "INSTAGRAM_VIDEO_URL_REQUIRED"


@pytest.mark.parametrize(
    "video_url",
    [
        "C:/video/test.mp4",
        "http://localhost/test.mp4",
        "http://127.0.0.1/test.mp4",
        "https://192.168.1.20/test.mp4",
    ],
)
def test_non_public_or_non_https_video_url_is_rejected(video_url: str):
    adapter = make_instagram_adapter(lambda request: httpx.Response(500))
    with pytest.raises(InstagramPublishError):
        adapter.build_platform_payload(publish_request(video_url=video_url))


def test_access_token_is_redacted_from_errors_and_logs(monkeypatch):
    captured = CapturingLogger()
    monkeypatch.setattr("app.adapters.publishing.instagram.logger", captured)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400,
            json={
                "error": {
                    "message": f"bad access_token={ACCESS_TOKEN}",
                    "type": "OAuthException",
                    "code": 190,
                }
            },
        )

    with pytest.raises(InstagramPublishError) as exc_info:
        asyncio.run(make_instagram_adapter(handler).publish_video(publish_request()))

    assert ACCESS_TOKEN not in str(exc_info.value)
    assert ACCESS_TOKEN not in repr(captured.entries)
    assert "[REDACTED]" in str(exc_info.value)


def test_media_publish_transport_failure_is_unknown_and_not_retried():
    publish_calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal publish_calls
        if request.url.path.endswith(f"/{IG_USER_ID}/media"):
            return httpx.Response(200, json={"id": "container_ambiguous"})
        if request.url.path.endswith("/container_ambiguous"):
            return httpx.Response(200, json={"status_code": "FINISHED"})
        publish_calls += 1
        raise httpx.ReadTimeout("publish response timed out", request=request)

    with pytest.raises(InstagramPublishError) as exc_info:
        asyncio.run(make_instagram_adapter(handler).publish_video(publish_request()))

    assert exc_info.value.error_code == "PUBLISH_RESULT_UNKNOWN"
    assert exc_info.value.container_id == "container_ambiguous"
    assert publish_calls == 1


def test_seed_adds_instagram_reel_configuration(db):
    _seed_publish_platforms(db)
    db.commit()
    platform = db.query(PublishPlatform).filter_by(code="instagram").one()

    assert platform.adapter_type == "instagram_graph"
    assert platform.api_base_url == "https://graph.instagram.com"
    assert platform.api_version == "v26.0"
    assert platform.extra_config["processing_timeout_seconds"] == 300
    assert platform.extra_config["require_https_video_url"] is True
    assert platform.capabilities["supports_reel"] is True
    assert platform.capabilities["supports_image"] is False
    assert {field["key"] for field in platform.capabilities["fields"]} == {
        "video_url",
        "caption",
        "share_to_feed",
    }


def test_publish_worker_persists_instagram_ids(db, make_user, make_video, make_platform, monkeypatch):
    user = make_user()
    video = make_video(user)
    platform, account = make_platform()
    platform.code = "instagram"
    task = PublishTask(
        video_id=video.id,
        user_id=user.id,
        platform_id=platform.id,
        account_id=account.id,
        title="Instagram success",
        tags=[],
        platform_payload={},
        platform_overrides={},
        idempotency_key="instagram-worker-success",
        status=PublishStatus.PENDING,
    )
    db.add(task)
    db.commit()

    class SuccessfulAdapter:
        async def publish_video(self, request):
            return PublishResult(
                status="success",
                provider_container_id="container_saved",
                platform_post_id="media_saved",
                publish_url="https://www.instagram.com/reel/WORKER123/",
                platform_url="https://www.instagram.com/worker.creator/",
            )

    monkeypatch.setattr(
        "app.tasks.publish_tasks.PublishAdapterFactory.create",
        lambda platform, account: SuccessfulAdapter(),
    )
    run_publish_task.run(str(task.id))
    db.expire_all()
    saved = db.get(PublishTask, task.id)
    assert saved.status == PublishStatus.SUCCESS
    assert saved.provider_container_id == "container_saved"
    assert saved.platform_post_id == "media_saved"
    assert saved.publish_url == "https://www.instagram.com/p/WORKER123/"
    assert saved.platform_url == "https://www.instagram.com/worker.creator/"
    response = PublishTaskOut.from_model(
        saved,
        platform_name="Instagram",
        account_name="Instagram test account",
    )
    assert response.provider_container_id == "container_saved"
    assert response.platform_post_id == "media_saved"
    assert response.publish_url == "https://www.instagram.com/p/WORKER123/"
    assert response.platform_url == "https://www.instagram.com/worker.creator/"


def test_publish_worker_persists_structured_error_and_container(
    db,
    make_user,
    make_video,
    make_platform,
    monkeypatch,
):
    user = make_user()
    video = make_video(user)
    platform, account = make_platform()
    task = PublishTask(
        video_id=video.id,
        user_id=user.id,
        platform_id=platform.id,
        account_id=account.id,
        title="Instagram failure",
        tags=[],
        platform_payload={},
        platform_overrides={},
        idempotency_key="instagram-worker-failure",
        status=PublishStatus.PENDING,
    )
    db.add(task)
    db.commit()

    class FailingAdapter:
        async def publish_video(self, request):
            raise InstagramPublishError(
                "PUBLISH_RESULT_UNKNOWN",
                "Manual verification is required",
                stage="PUBLISH_MEDIA",
                container_id="container_unknown",
            )

    monkeypatch.setattr(
        "app.tasks.publish_tasks.PublishAdapterFactory.create",
        lambda platform, account: FailingAdapter(),
    )
    run_publish_task.run(str(task.id))
    db.expire_all()
    saved = db.get(PublishTask, task.id)
    assert saved.status == PublishStatus.FAILED
    assert saved.error_code == "PUBLISH_RESULT_UNKNOWN"
    assert saved.provider_container_id == "container_unknown"
