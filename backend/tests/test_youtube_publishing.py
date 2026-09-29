import asyncio
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest

from app.adapters.publishing.base import PublishRequest
from app.adapters.publishing.youtube import (
    YOUTUBE_READONLY_SCOPE,
    YOUTUBE_UPLOAD_SCOPE,
    YouTubePublishAdapter,
    YouTubePublishError,
)
from app.core.security import decrypt_secret, encrypt_secret
from app.core.enums import PublishStatus
from app.db.init_db import _seed_publish_platforms
from app.models import PublishAccount, PublishPlatform, PublishTask
from app.tasks.publish_tasks import run_publish_task


ACCESS_TOKEN = "youtube-access-token-secret"
REFRESH_TOKEN = "youtube-refresh-token-secret"
CLIENT_ID = "youtube-client-id-secret"
CLIENT_SECRET = "youtube-client-secret-secret"
VIDEO_ID = "yt_video_123"
CHUNK_SIZE = 256 * 1024


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


def make_adapter(
    handler,
    *,
    clock: FakeClock | None = None,
    processing_timeout_seconds: float = 5,
    token_expires_at: datetime | None = None,
    account: PublishAccount | None = None,
    platform: PublishPlatform | None = None,
    max_retries: int = 1,
) -> YouTubePublishAdapter:
    platform = platform or PublishPlatform(
        name="YouTube",
        code="youtube",
        adapter_type="youtube_data_api_v3",
        api_base_url="https://api.example/youtube/v3",
        auth_type="oauth2",
        capabilities={"supports_video": True},
        extra_config={
            "upload_base_url": "https://upload.example/youtube/v3",
            "token_uri": "https://oauth.example/token",
            "poll_interval_seconds": 1,
            "processing_timeout_seconds": processing_timeout_seconds,
            "http_timeout_seconds": 3,
            "upload_chunk_size": CHUNK_SIZE,
            "max_retries": max_retries,
            "retry_backoff_seconds": 0.1,
        },
        enabled=True,
    )
    account = account or PublishAccount(
        platform_id=platform.id,
        name="YouTube test account",
        account_identifier="youtube-test",
        channel_id="UC_TEST_CHANNEL",
        client_id_encrypted=encrypt_secret(CLIENT_ID),
        client_secret_encrypted=encrypt_secret(CLIENT_SECRET),
        access_token_encrypted=encrypt_secret(ACCESS_TOKEN),
        refresh_token_encrypted=encrypt_secret(REFRESH_TOKEN),
        token_expires_at=token_expires_at,
        authorized_scopes=[YOUTUBE_UPLOAD_SCOPE, YOUTUBE_READONLY_SCOPE],
        extra_config={},
        enabled=True,
    )
    selected_clock = clock or FakeClock()
    return YouTubePublishAdapter(
        platform,
        account,
        transport=httpx.MockTransport(handler),
        sleep=selected_clock.sleep,
        monotonic=selected_clock,
    )


def make_request(
    video_path: Path,
    *,
    progress_callback=None,
    existing_platform_post_id: str | None = None,
    platform_payload: dict | None = None,
) -> PublishRequest:
    return PublishRequest(
        video_path=video_path,
        title="YouTube test",
        content="Common content",
        description="Test description",
        tags=["ai", "video"],
        publish_type="video",
        common_payload={},
        platform_payload=platform_payload or {},
        overrides={},
        idempotency_key="youtube-test-request",
        progress_callback=progress_callback,
        existing_platform_post_id=existing_platform_post_id,
    )


def upload_then_status_handler(statuses: list[str], seen: list[httpx.Request] | None = None):
    status_index = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal status_index
        if seen is not None:
            seen.append(request)
        if request.method == "POST" and request.url.path.endswith("/youtube/v3/videos"):
            return httpx.Response(200, headers={"Location": "https://upload.example/session"})
        if request.method == "PUT" and request.url.path == "/session":
            return httpx.Response(200, json={"id": VIDEO_ID})
        if request.method == "GET" and request.url.path.endswith("/youtube/v3/videos"):
            status = statuses[min(status_index, len(statuses) - 1)]
            status_index += 1
            return httpx.Response(
                200,
                json={"items": [{"id": VIDEO_ID, "processingDetails": {"processingStatus": status}}]},
            )
        raise AssertionError(f"Unexpected request: {request.method} {request.url}")

    return handler


def google_error(status: int, reason: str, message: str = "request rejected") -> httpx.Response:
    return httpx.Response(
        status,
        json={"error": {"message": message, "errors": [{"reason": reason}]}},
    )


def test_payload_defaults_to_private_category_22_and_supported_metadata(tmp_path: Path):
    adapter = make_adapter(lambda request: httpx.Response(500))
    payload = adapter.build_platform_payload(make_request(tmp_path / "video.mp4"))

    assert payload == {
        "snippet": {
            "title": "YouTube test",
            "description": "Test description",
            "tags": ["ai", "video"],
            "categoryId": "22",
        },
        "status": {
            "privacyStatus": "private",
            "selfDeclaredMadeForKids": False,
            "containsSyntheticMedia": True,
        },
    }


def test_resumable_upload_uses_local_file_and_returns_video_id(tmp_path: Path):
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"video-content")
    seen: list[httpx.Request] = []

    result = asyncio.run(
        make_adapter(upload_then_status_handler(["succeeded"], seen=seen)).publish_video(
            make_request(video, platform_payload={"privacy_status": "unlisted", "category_id": "24"})
        )
    )

    assert result.status == "success"
    assert result.platform_post_id == VIDEO_ID
    assert result.platform_post_url == f"https://www.youtube.com/watch?v={VIDEO_ID}"
    assert result.publish_url == f"https://www.youtube.com/watch?v={VIDEO_ID}"
    assert result.platform_url == "https://www.youtube.com/channel/UC_TEST_CHANNEL"
    create_request = seen[0]
    assert create_request.url.params["uploadType"] == "resumable"
    assert create_request.url.params["part"] == "snippet,status"
    assert create_request.headers["Authorization"] == f"Bearer {ACCESS_TOKEN}"
    assert create_request.headers["X-Upload-Content-Length"] == str(video.stat().st_size)
    assert json.loads(create_request.content)["status"]["privacyStatus"] == "unlisted"


def test_chunked_upload_reports_10_50_and_100_percent(tmp_path: Path):
    video = tmp_path / "large.mp4"
    video.write_bytes(b"x" * CHUNK_SIZE * 10)
    progress: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(200, headers={"Location": "https://upload.example/session"})
        if request.method == "GET":
            return httpx.Response(
                200,
                json={"items": [{"processingDetails": {"processingStatus": "succeeded"}}]},
            )
        content_range = request.headers["Content-Range"]
        end = int(content_range.split("-")[1].split("/")[0])
        if end + 1 < video.stat().st_size:
            return httpx.Response(308, headers={"Range": f"bytes=0-{end}"})
        return httpx.Response(200, json={"id": VIDEO_ID})

    result = asyncio.run(
        make_adapter(handler).publish_video(make_request(video, progress_callback=progress.append))
    )

    assert result.status == "success"
    assert 10 in progress
    assert 50 in progress
    assert progress[-1] == 100


def test_expired_access_token_is_refreshed_and_persisted_without_losing_refresh_token(
    db, tmp_path: Path
):
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"video")
    platform = PublishPlatform(
        name="YouTube",
        code="youtube",
        adapter_type="youtube_data_api_v3",
        api_base_url="https://api.example/youtube/v3",
        auth_type="oauth2",
        capabilities={},
        extra_config={
            "upload_base_url": "https://upload.example/youtube/v3",
            "token_uri": "https://oauth.example/token",
            "poll_interval_seconds": 1,
            "processing_timeout_seconds": 5,
            "http_timeout_seconds": 3,
            "upload_chunk_size": CHUNK_SIZE,
            "max_retries": 1,
            "retry_backoff_seconds": 0.1,
        },
        enabled=True,
    )
    db.add(platform)
    db.flush()
    account = PublishAccount(
        platform_id=platform.id,
        name="YouTube persisted account",
        client_id_encrypted=encrypt_secret(CLIENT_ID),
        client_secret_encrypted=encrypt_secret(CLIENT_SECRET),
        access_token_encrypted=encrypt_secret("expired-token"),
        refresh_token_encrypted=encrypt_secret(REFRESH_TOKEN),
        token_expires_at=datetime.now(UTC) - timedelta(minutes=1),
        authorized_scopes=[YOUTUBE_UPLOAD_SCOPE, YOUTUBE_READONLY_SCOPE],
        extra_config={},
        enabled=True,
    )
    db.add(account)
    db.commit()
    token_calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal token_calls
        if request.url.path == "/token":
            token_calls += 1
            assert b"refresh_token=youtube-refresh-token-secret" in request.content
            return httpx.Response(200, json={"access_token": "new-access-token", "expires_in": 7200})
        return upload_then_status_handler(["succeeded"])(request)

    asyncio.run(
        make_adapter(handler, account=account, platform=platform).publish_video(make_request(video))
    )
    db.expire_all()
    persisted = db.get(PublishAccount, account.id)

    assert token_calls == 1
    assert decrypt_secret(persisted.access_token_encrypted) == "new-access-token"
    assert decrypt_secret(persisted.refresh_token_encrypted) == REFRESH_TOKEN
    assert persisted.token_expires_at is not None


def test_invalid_grant_maps_to_reauthorization_and_does_not_upload(tmp_path: Path):
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        return httpx.Response(400, json={"error": "invalid_grant", "error_description": "revoked"})

    adapter = make_adapter(
        handler, token_expires_at=datetime.now(UTC) - timedelta(seconds=1)
    )
    with pytest.raises(YouTubePublishError) as exc_info:
        asyncio.run(adapter.publish_video(make_request(tmp_path / "unused.mp4")))

    assert exc_info.value.error_code == "YOUTUBE_REAUTH_REQUIRED"
    assert exc_info.value.stage == "REFRESH_TOKEN"
    assert calls == ["/token"]


def test_unauthorized_upload_refreshes_token_once_and_retries(tmp_path: Path):
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"video")
    create_calls = 0
    token_calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal create_calls, token_calls
        if request.url.path == "/token":
            token_calls += 1
            return httpx.Response(200, json={"access_token": "refreshed-after-401", "expires_in": 3600})
        if request.method == "POST":
            create_calls += 1
            if create_calls == 1:
                return httpx.Response(401, json={"error": {"message": "expired"}})
            assert request.headers["Authorization"] == "Bearer refreshed-after-401"
            return httpx.Response(200, headers={"Location": "https://upload.example/session"})
        if request.method == "PUT":
            assert request.headers["Authorization"] == "Bearer refreshed-after-401"
            return httpx.Response(200, json={"id": VIDEO_ID})
        return httpx.Response(
            200,
            json={"items": [{"processingDetails": {"processingStatus": "succeeded"}}]},
        )

    result = asyncio.run(make_adapter(handler).publish_video(make_request(video)))

    assert result.status == "success"
    assert create_calls == 2
    assert token_calls == 1


@pytest.mark.parametrize(
    ("reason", "expected"),
    [
        ("insufficientPermissions", "YOUTUBE_SCOPE_INSUFFICIENT"),
        ("youtubeSignupRequired", "YOUTUBE_CHANNEL_REQUIRED"),
        ("quotaExceeded", "QUOTA_EXCEEDED"),
        ("dailyLimitExceeded", "QUOTA_EXCEEDED"),
    ],
)
def test_official_google_reasons_are_mapped(reason: str, expected: str, tmp_path: Path):
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"video")

    def handler(request: httpx.Request) -> httpx.Response:
        return google_error(403, reason)

    with pytest.raises(YouTubePublishError) as exc_info:
        asyncio.run(make_adapter(handler).publish_video(make_request(video)))

    assert exc_info.value.error_code == expected
    assert exc_info.value.stage == "CREATE_UPLOAD"
    assert exc_info.value.http_status == 403


def test_processing_poll_transitions_from_processing_to_succeeded(tmp_path: Path):
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"video")

    result = asyncio.run(
        make_adapter(upload_then_status_handler(["processing", "succeeded"])).publish_video(
            make_request(video)
        )
    )

    assert result.status == "success"
    assert result.metadata == {"video_id": VIDEO_ID, "processing_status": "succeeded"}


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        ("failed", "YOUTUBE_PROCESSING_FAILED"),
        ("terminated", "YOUTUBE_PROCESSING_TERMINATED"),
    ],
)
def test_terminal_processing_failures_are_structured(status: str, expected: str, tmp_path: Path):
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"video")

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(200, headers={"Location": "https://upload.example/session"})
        if request.method == "PUT":
            return httpx.Response(200, json={"id": VIDEO_ID})
        details = {"processingStatus": status}
        if status == "failed":
            details["processingFailureReason"] = "codec"
        return httpx.Response(200, json={"items": [{"processingDetails": details}]})

    with pytest.raises(YouTubePublishError) as exc_info:
        asyncio.run(
            make_adapter(handler).publish_video(make_request(video))
        )

    assert exc_info.value.error_code == expected
    assert exc_info.value.video_id == VIDEO_ID
    assert exc_info.value.stage == "CHECK_PROCESSING"
    assert exc_info.value.reason == ("codec" if status == "failed" else "terminated")


def test_processing_timeout_retains_video_id_for_safe_retry(tmp_path: Path):
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"video")
    clock = FakeClock()

    with pytest.raises(YouTubePublishError) as exc_info:
        asyncio.run(
            make_adapter(
                upload_then_status_handler(["processing"]),
                clock=clock,
                processing_timeout_seconds=2,
            ).publish_video(make_request(video))
        )

    error = exc_info.value
    assert error.error_code == "PROCESSING_TIMEOUT"
    assert error.retryable is True
    assert error.video_id == VIDEO_ID


def test_existing_video_id_skips_file_validation_and_upload(tmp_path: Path):
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.method)
        assert request.method == "GET"
        return httpx.Response(
            200,
            json={"items": [{"processingDetails": {"processingStatus": "succeeded"}}]},
        )

    result = asyncio.run(
        make_adapter(handler).publish_video(
            make_request(tmp_path / "missing.mp4", existing_platform_post_id=VIDEO_ID)
        )
    )

    assert result.platform_post_id == VIDEO_ID
    assert calls == ["GET"]


def test_missing_local_file_fails_before_any_http_request(tmp_path: Path):
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(500)

    with pytest.raises(YouTubePublishError) as exc_info:
        asyncio.run(make_adapter(handler).publish_video(make_request(tmp_path / "missing.mp4")))

    assert exc_info.value.error_code == "YOUTUBE_FILE_NOT_FOUND"
    assert exc_info.value.stage == "VALIDATE_FILE"
    assert calls == 0


def test_secret_values_are_removed_from_errors_and_logs(tmp_path: Path, monkeypatch):
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"video")
    leaked_message = (
        f"Bearer {ACCESS_TOKEN} refresh_token={REFRESH_TOKEN} "
        f"client_secret={CLIENT_SECRET}"
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return google_error(400, "badRequest", leaked_message)

    capturing_logger = CapturingLogger()
    monkeypatch.setattr("app.adapters.publishing.youtube.logger", capturing_logger)
    with pytest.raises(YouTubePublishError) as exc_info:
        asyncio.run(make_adapter(handler).publish_video(make_request(video)))

    rendered = str(exc_info.value)
    logged = json.dumps(capturing_logger.entries)
    assert ACCESS_TOKEN not in rendered
    assert REFRESH_TOKEN not in rendered
    assert CLIENT_SECRET not in rendered
    assert "[REDACTED]" in rendered
    assert ACCESS_TOKEN not in logged
    assert REFRESH_TOKEN not in logged
    assert CLIENT_SECRET not in logged


@pytest.mark.parametrize(
    ("status", "expected", "retryable"),
    [
        (400, "YOUTUBE_INVALID_REQUEST", False),
        (401, "YOUTUBE_UNAUTHORIZED", False),
        (403, "YOUTUBE_FORBIDDEN", False),
        (404, "YOUTUBE_VIDEO_NOT_FOUND", False),
        (503, "YOUTUBE_TEMPORARY_FAILURE", True),
    ],
)
def test_http_status_families_remain_distinguishable(
    status: int, expected: str, retryable: bool, tmp_path: Path
):
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"video")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json={"error": {"message": "failure"}})

    with pytest.raises(YouTubePublishError) as exc_info:
        asyncio.run(make_adapter(handler, max_retries=0).publish_video(make_request(video)))

    assert exc_info.value.error_code == expected
    assert exc_info.value.retryable is retryable


def test_network_error_is_structured_and_retryable(tmp_path: Path):
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"video")

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("network unavailable", request=request)

    with pytest.raises(YouTubePublishError) as exc_info:
        asyncio.run(make_adapter(handler, max_retries=0).publish_video(make_request(video)))

    assert exc_info.value.error_code == "YOUTUBE_NETWORK_ERROR"
    assert exc_info.value.retryable is True
    assert exc_info.value.stage == "CREATE_UPLOAD"


def test_configuration_requires_both_official_oauth_scopes():
    adapter = make_adapter(lambda request: httpx.Response(500))
    adapter.account.authorized_scopes = [YOUTUBE_UPLOAD_SCOPE]

    configured, _, details = adapter.configuration_status()

    assert configured is False
    assert "authorized_scopes" in details["missing"]
    assert details["missing_scopes"] == [YOUTUBE_READONLY_SCOPE]


def test_seed_adds_youtube_upload_configuration(db):
    _seed_publish_platforms(db)
    db.commit()
    platform = db.query(PublishPlatform).filter_by(code="youtube").one()

    assert platform.adapter_type == "youtube_data_api_v3"
    assert platform.extra_config["upload_chunk_size"] == 8 * 1024 * 1024
    assert platform.extra_config["processing_timeout_seconds"] == 600
    assert {field["key"] for field in platform.capabilities["fields"]} == {
        "privacy_status",
        "category_id",
        "self_declared_made_for_kids",
        "contains_synthetic_media",
    }


def test_worker_persists_video_id_when_processing_times_out(
    db, make_user, make_video, make_platform, monkeypatch
):
    user = make_user()
    video = make_video(user)
    platform, account = make_platform()
    task = PublishTask(
        video_id=video.id,
        user_id=user.id,
        platform_id=platform.id,
        account_id=account.id,
        title="YouTube timeout",
        tags=[],
        platform_payload={},
        platform_overrides={},
        idempotency_key="youtube-worker-timeout",
        status=PublishStatus.PENDING,
    )
    db.add(task)
    db.commit()

    class TimeoutAdapter:
        async def publish_video(self, request):
            raise YouTubePublishError(
                "PROCESSING_TIMEOUT",
                "processing continues",
                stage="CHECK_PROCESSING",
                retryable=True,
                video_id=VIDEO_ID,
            )

    monkeypatch.setattr(
        "app.tasks.publish_tasks.PublishAdapterFactory.create",
        lambda selected_platform, selected_account: TimeoutAdapter(),
    )
    run_publish_task.run(str(task.id))
    db.expire_all()
    saved = db.get(PublishTask, task.id)

    assert saved.status == PublishStatus.FAILED
    assert saved.error_code == "PROCESSING_TIMEOUT"
    assert saved.platform_post_id == VIDEO_ID
    assert saved.platform_post_url == f"https://www.youtube.com/watch?v={VIDEO_ID}"
