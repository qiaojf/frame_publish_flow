import asyncio
import base64
import json
import struct
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest

from app.adapters.video_models.base import (
    GeneratedVideo,
    GenerationRequest,
    VideoModelAdapterError,
)
from app.adapters.video_models.minimax_client import MiniMaxClient
from app.adapters.video_models.minimax_hailuo23 import MiniMaxHailuo23Adapter
from app.core.config import get_settings
from app.core.enums import GenerationStatus, GenerationType, UserRole
from app.core.security import decrypt_secret, encrypt_secret
from app.db.init_db import _seed_models
from app.models import ModelAccount, ModelProvider, Video, VideoGenerationTask, VideoModel
from app.tasks.generation_tasks import run_generation_task
from app.utils.media import VideoMetadata


def png_header(width: int, height: int) -> bytes:
    return b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + struct.pack(">II", width, height)


def make_minimax_model(
    db,
    *,
    account_enabled: bool = True,
    model_enabled: bool = True,
) -> VideoModel:
    suffix = uuid.uuid4().hex
    provider = ModelProvider(
        name="MiniMax",
        code=f"minimax-test-{suffix}",
        adapter_family="minimax",
        default_api_base_url="https://api.minimax.io",
        auth_type="bearer_token",
        provider_capabilities={
            "video_generation": True,
            "async_task": True,
            "file_retrieve": True,
        },
        extra_config={},
        enabled=True,
    )
    db.add(provider)
    db.flush()
    account = ModelAccount(
        provider_id=provider.id,
        name="MiniMax PoC Account",
        account_identifier=f"minimax-test-{suffix}",
        api_version="v1",
        api_key_encrypted=encrypt_secret("minimax-test-secret"),
        credential_extra={},
        extra_config={},
        enabled=account_enabled,
    )
    db.add(account)
    db.flush()
    model = VideoModel(
        model_account_id=account.id,
        name="MiniMax Hailuo 2.3",
        code=f"minimax_hailuo_2_3_test_{suffix}",
        model_id="MiniMax-Hailuo-2.3",
        adapter_type="minimax_hailuo23",
        supports_text_to_video=True,
        supports_image_to_video=True,
        capabilities={
            "text_to_video": True,
            "image_to_video": True,
            "prompt": {
                "required_for_text_to_video": True,
                "required_for_image_to_video": False,
                "max_length": 2000,
            },
            "durations": [6, 10],
            "resolutions": ["768P", "1080P"],
            "resolution_duration_matrix": {"768P": [6, 10], "1080P": [6]},
            "max_images": 1,
            "image": {
                "formats": ["jpg", "jpeg", "png", "webp"],
                "max_size_mb_exclusive": 20,
                "short_edge_min_exclusive": 300,
                "aspect_ratio_min": 0.4,
                "aspect_ratio_max": 2.5,
                "supports_public_url": True,
                "supports_base64_data_url": True,
            },
            "parameter_combination_error_code": "INVALID_MODEL_PARAMETER_COMBINATION",
        },
        request_defaults={
            "duration": 6,
            "resolution": "768P",
            "prompt_optimizer": True,
            "fast_pretreatment": False,
        },
        extra_config={},
        timeout_seconds=900,
        enabled=model_enabled,
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    return model


def adapter_with_transport(model: VideoModel, handler) -> MiniMaxHailuo23Adapter:
    client = MiniMaxClient(
        base_url="https://api.minimax.io",
        api_key="minimax-test-secret",
        timeout_seconds=60,
        transport=httpx.MockTransport(handler),
    )
    return MiniMaxHailuo23Adapter(model, client=client)


def test_seed_creates_enabled_minimax_three_layer_configuration(db):
    _seed_models(db, get_settings())
    db.commit()
    provider = db.query(ModelProvider).filter_by(code="minimax").one()
    account = db.query(ModelAccount).filter_by(provider_id=provider.id).one()
    model = db.query(VideoModel).filter_by(code="minimax_hailuo_2_3").one()

    assert provider.enabled is True
    assert provider.auth_type == "bearer_token"
    assert provider.provider_capabilities == {
        "video_generation": True,
        "async_task": True,
        "file_retrieve": True,
    }
    assert account.name == "MiniMax PoC Account"
    assert account.api_version == "v1"
    assert account.enabled is True
    assert model.model_account_id == account.id
    assert model.enabled is True
    assert model.request_defaults["resolution"] == "768P"
    assert model.capabilities["resolution_duration_matrix"]["1080P"] == [6]


def test_seed_upgrades_legacy_minimax_template_without_losing_api_key(db):
    provider = ModelProvider(
        name="MiniMax",
        code="minimax",
        adapter_family="minimax",
        default_api_base_url="https://api.minimax.io",
        auth_type="api_key",
        provider_capabilities={},
        extra_config={"custom_provider_option": True},
        enabled=False,
    )
    db.add(provider)
    db.flush()
    account = ModelAccount(
        provider_id=provider.id,
        name="MiniMax Template Account",
        account_identifier="minimax-default",
        api_key_encrypted=encrypt_secret("preserved-key"),
        credential_extra={},
        extra_config={"custom_account_option": True},
        enabled=False,
    )
    db.add(account)
    db.flush()
    model = VideoModel(
        model_account_id=account.id,
        name="MiniMax Hailuo 2.3",
        code="minimax-hailuo-2.3",
        model_id="MiniMax-Hailuo-2.3",
        adapter_type="minimax_hailuo23",
        supports_text_to_video=True,
        supports_image_to_video=True,
        capabilities={"custom_capability": True},
        request_defaults={},
        extra_config={"callback_url": "https://example.test/callback"},
        timeout_seconds=300,
        enabled=False,
    )
    db.add(model)
    db.commit()

    _seed_models(db, get_settings())
    db.commit()
    db.refresh(provider)
    db.refresh(account)
    db.refresh(model)

    assert provider.auth_type == "bearer_token"
    assert provider.enabled is True
    assert provider.extra_config["custom_provider_option"] is True
    assert account.name == "MiniMax PoC Account"
    assert account.enabled is True
    assert account.extra_config["custom_account_option"] is True
    assert decrypt_secret(account.api_key_encrypted) == "preserved-key"
    assert model.code == "minimax_hailuo_2_3"
    assert model.enabled is True
    assert model.capabilities["custom_capability"] is True
    assert model.extra_config["callback_url"] == "https://example.test/callback"


def test_minimax_account_test_only_validates_local_configuration(
    client, db, make_user, auth_headers, monkeypatch
):
    admin = make_user(username="minimax-admin", role=UserRole.ADMIN)
    model = make_minimax_model(db)

    async def forbidden_real_call(*args, **kwargs):
        raise AssertionError("account test must not call POST /v1/video_generation")

    monkeypatch.setattr(MiniMaxClient, "create_video", forbidden_real_call)
    response = client.post(
        f"/api/v1/admin/model-accounts/{model.model_account_id}/test",
        headers=auth_headers(admin),
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["configured"] is True
    assert data["details"]["credential_configured"] is True
    assert data["details"]["real_api_verified"] is False
    assert "minimax-test-secret" not in response.text


def test_text_to_video_request_uses_official_payload_and_preserves_camera_commands(db):
    model = make_minimax_model(db)
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["authorization"] = request.headers["Authorization"]
        captured["json"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "task_id": "test_task_001",
                "base_resp": {"status_code": 0, "status_msg": "success"},
            },
        )

    adapter = adapter_with_transport(model, handler)
    provider_id = asyncio.run(
        adapter.create_text_to_video(
            GenerationRequest(
                prompt="A robot walks [Pan left] then stops [Static shot].",
                duration=6,
                aspect_ratio="16:9",
                resolution="1080P",
            )
        )
    )

    assert provider_id == "test_task_001"
    assert captured["path"] == "/v1/video_generation"
    assert captured["authorization"] == "Bearer minimax-test-secret"
    assert captured["json"] == {
        "model": "MiniMax-Hailuo-2.3",
        "prompt": "A robot walks [Pan left] then stops [Static shot].",
        "prompt_optimizer": True,
        "fast_pretreatment": False,
        "duration": 6,
        "resolution": "1080P",
    }


def test_image_to_video_supports_base64_data_url_and_public_url(db, tmp_path):
    model = make_minimax_model(db)
    payloads = []

    def handler(request: httpx.Request) -> httpx.Response:
        payloads.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "task_id": f"task-{len(payloads)}",
                "base_resp": {"status_code": 0, "status_msg": "success"},
            },
        )

    adapter = adapter_with_transport(model, handler)
    source = tmp_path / "frame.png"
    source.write_bytes(png_header(640, 480))
    asyncio.run(
        adapter.create_image_to_video(
            GenerationRequest("", 6, None, "768P", source_image_path=source)
        )
    )
    asyncio.run(
        adapter.create_image_to_video(
            GenerationRequest(
                "move",
                6,
                None,
                "768P",
                source_image_url="https://cdn.example/frame.webp",
            )
        )
    )

    assert payloads[0]["first_frame_image"].startswith("data:image/png;base64,")
    encoded = payloads[0]["first_frame_image"].split(",", 1)[1]
    assert base64.b64decode(encoded) == source.read_bytes()
    assert "prompt" not in payloads[0]
    assert payloads[1]["first_frame_image"] == "https://cdn.example/frame.webp"


@pytest.mark.parametrize(
    ("remote_status", "expected"),
    [
        ("Preparing", "pending"),
        ("Queueing", "pending"),
        ("Processing", "processing"),
        ("Success", "success"),
        ("Fail", "failed"),
    ],
)
def test_minimax_status_mapping(db, remote_status, expected):
    model = make_minimax_model(db)

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["task_id"] == "task-123"
        return httpx.Response(
            200,
            json={
                "task_id": "task-123",
                "status": remote_status,
                "base_resp": {"status_code": 0, "status_msg": "success"},
            },
        )

    adapter = adapter_with_transport(model, handler)
    assert asyncio.run(adapter.get_task_status("task-123")) == expected


def test_minimax_base_resp_error_is_sanitized(db):
    model = make_minimax_model(db)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "base_resp": {
                    "status_code": 1008,
                    "status_msg": "insufficient balance for minimax-test-secret",
                }
            },
        )

    adapter = adapter_with_transport(model, handler)
    with pytest.raises(VideoModelAdapterError) as exc_info:
        asyncio.run(
            adapter.create_text_to_video(
                GenerationRequest("test", 6, None, "768P")
            )
        )
    assert exc_info.value.error_code == "MINIMAX_INSUFFICIENT_BALANCE"
    assert "minimax-test-secret" not in str(exc_info.value)


@pytest.mark.parametrize(
    ("http_status", "expected_code"),
    [
        (401, "MINIMAX_AUTH_FAILED"),
        (402, "MINIMAX_INSUFFICIENT_BALANCE"),
        (422, "MINIMAX_INVALID_PARAMETER"),
        (429, "MINIMAX_RATE_LIMITED"),
        (503, "MINIMAX_SERVICE_UNAVAILABLE"),
    ],
)
def test_minimax_http_errors_are_mapped_to_safe_codes(db, http_status, expected_code):
    model = make_minimax_model(db)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(http_status, text="upstream detail must not reach the user")

    adapter = adapter_with_transport(model, handler)
    with pytest.raises(VideoModelAdapterError) as exc_info:
        asyncio.run(
            adapter.create_text_to_video(
                GenerationRequest("test", 6, None, "768P")
            )
        )
    assert exc_info.value.error_code == expected_code
    assert "upstream detail" not in str(exc_info.value)


def test_minimax_retrieve_and_stream_download(db, tmp_path):
    model = make_minimax_model(db)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/query/video_generation":
            return httpx.Response(
                200,
                json={
                    "task_id": "task-123",
                    "status": "Success",
                    "file_id": "file-456",
                    "base_resp": {"status_code": 0, "status_msg": "success"},
                },
            )
        if request.url.path == "/v1/files/retrieve":
            assert request.url.params["file_id"] == "file-456"
            return httpx.Response(
                200,
                json={
                    "file": {"file_id": "file-456", "download_url": "https://cdn.example/video.mp4"},
                    "base_resp": {"status_code": 0, "status_msg": "success"},
                },
            )
        if request.url.host == "cdn.example":
            assert "Authorization" not in request.headers
            return httpx.Response(200, content=b"streamed-mp4-bytes")
        raise AssertionError(f"unexpected request: {request.url}")

    adapter = adapter_with_transport(model, handler)
    assert asyncio.run(adapter.get_task_status("task-123")) == "success"
    result = asyncio.run(adapter.get_result("task-123", tmp_path))
    assert result.local_path.suffix == ".mp4"
    assert result.local_path.read_bytes() == b"streamed-mp4-bytes"


@pytest.mark.parametrize(
    ("duration", "resolution", "accepted"),
    [(6, "768P", True), (6, "1080P", True), (10, "768P", True), (10, "1080P", False)],
)
def test_generation_api_validates_minimax_resolution_duration_matrix(
    client, db, make_user, auth_headers, monkeypatch, duration, resolution, accepted
):
    monkeypatch.setattr("app.tasks.generation_tasks.run_generation_task.delay", lambda task_id: None)
    user = make_user(username=f"matrix-{duration}-{resolution}")
    model = make_minimax_model(db)
    response = client.post(
        "/api/v1/generation/tasks",
        headers=auth_headers(user),
        data={
            "prompt": "matrix validation",
            "model_id": str(model.id),
            "duration": str(duration),
            "resolution": resolution,
        },
    )
    assert response.status_code == (202 if accepted else 400)
    if not accepted:
        assert response.json()["error_code"] == "INVALID_MODEL_PARAMETER_COMBINATION"


def test_minimax_image_constraints_are_checked_before_queue(
    client, db, make_user, auth_headers, monkeypatch
):
    queued = []
    monkeypatch.setattr(
        "app.tasks.generation_tasks.run_generation_task.delay", lambda task_id: queued.append(task_id)
    )
    user = make_user(username="image-validation")
    model = make_minimax_model(db)
    too_small = client.post(
        "/api/v1/generation/tasks",
        headers=auth_headers(user),
        data={"prompt": "", "model_id": str(model.id)},
        files={"image": ("small.png", png_header(300, 500), "image/png")},
    )
    invalid_ratio = client.post(
        "/api/v1/generation/tasks",
        headers=auth_headers(user),
        data={"prompt": "", "model_id": str(model.id)},
        files={"image": ("wide.png", png_header(1000, 301), "image/png")},
    )
    valid = client.post(
        "/api/v1/generation/tasks",
        headers=auth_headers(user),
        data={"prompt": "", "model_id": str(model.id)},
        files={"image": ("valid.png", png_header(640, 480), "image/png")},
    )

    assert too_small.status_code == 400
    assert too_small.json()["error_code"] == "IMAGE_DIMENSIONS_TOO_SMALL"
    assert invalid_ratio.status_code == 400
    assert invalid_ratio.json()["error_code"] == "INVALID_IMAGE_ASPECT_RATIO"
    assert valid.status_code == 202
    assert len(queued) == 1


def test_disabled_minimax_account_and_model_are_rejected_before_queue(
    client, db, make_user, auth_headers, monkeypatch
):
    monkeypatch.setattr("app.tasks.generation_tasks.run_generation_task.delay", lambda task_id: None)
    user = make_user(username="disabled-check")
    account_disabled = make_minimax_model(db, account_enabled=False)
    disabled_account_response = client.post(
        "/api/v1/generation/tasks",
        headers=auth_headers(user),
        data={"prompt": "test", "model_id": str(account_disabled.id)},
    )
    model_disabled = make_minimax_model(db, model_enabled=False)
    disabled_model_response = client.post(
        "/api/v1/generation/tasks",
        headers=auth_headers(user),
        data={"prompt": "test", "model_id": str(model_disabled.id)},
    )
    assert disabled_account_response.json()["error_code"] == "MODEL_ACCOUNT_DISABLED"
    assert disabled_model_response.json()["error_code"] == "MODEL_DISABLED"


def test_full_mocked_minimax_celery_chain_creates_video(
    db, make_user, monkeypatch
):
    user = make_user(username="minimax-worker")
    model = make_minimax_model(db)
    task = VideoGenerationTask(
        user_id=user.id,
        model_id=model.id,
        generation_type=GenerationType.TEXT_TO_VIDEO,
        prompt="mocked full chain",
        duration=6,
        resolution="768P",
        status=GenerationStatus.PENDING,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    query_statuses = iter(["Preparing", "Processing", "Success"])
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, request.url.path))
        if request.method == "POST" and request.url.path == "/v1/video_generation":
            return httpx.Response(
                200,
                json={
                    "task_id": "full-task-001",
                    "base_resp": {"status_code": 0, "status_msg": "success"},
                },
            )
        if request.url.path == "/v1/query/video_generation":
            status = next(query_statuses)
            payload = {
                "task_id": "full-task-001",
                "status": status,
                "base_resp": {"status_code": 0, "status_msg": "success"},
            }
            if status == "Success":
                payload["file_id"] = "full-file-001"
            return httpx.Response(200, json=payload)
        if request.url.path == "/v1/files/retrieve":
            return httpx.Response(
                200,
                json={
                    "file": {"download_url": "https://cdn.example/full.mp4"},
                    "base_resp": {"status_code": 0, "status_msg": "success"},
                },
            )
        if request.url.host == "cdn.example":
            return httpx.Response(200, content=b"mock-mp4")
        raise AssertionError(f"unexpected request: {request.url}")

    adapter = adapter_with_transport(model, handler)
    monkeypatch.setattr(
        "app.tasks.generation_tasks.ModelAdapterFactory.create", lambda selected: adapter
    )
    scheduled = []
    monkeypatch.setattr(
        run_generation_task,
        "apply_async",
        lambda args, countdown: scheduled.append((args, countdown)),
    )
    monkeypatch.setattr(
        "app.tasks.generation_tasks.MediaProcessor.probe",
        lambda self, path: VideoMetadata(6, 1366, 768),
    )

    def fake_thumbnail(self, source: Path, target: Path) -> Path:
        target.write_bytes(b"jpg")
        return target

    monkeypatch.setattr(
        "app.tasks.generation_tasks.MediaProcessor.thumbnail", fake_thumbnail
    )

    for _ in range(4):
        run_generation_task.run(str(task.id))

    db.expire_all()
    saved = db.get(VideoGenerationTask, task.id)
    video = db.query(Video).filter_by(generation_task_id=task.id).one()
    assert saved.provider_task_id == "full-task-001"
    assert saved.status == GenerationStatus.SUCCESS
    assert video.width == 1366
    assert len(scheduled) == 3
    assert all(countdown == 10 for _, countdown in scheduled)
    assert calls == [
        ("POST", "/v1/video_generation"),
        ("GET", "/v1/query/video_generation"),
        ("GET", "/v1/query/video_generation"),
        ("GET", "/v1/query/video_generation"),
        ("GET", "/v1/files/retrieve"),
        ("GET", "/full.mp4"),
    ]


def test_minimax_failed_status_persists_specific_error_code(db, make_user, monkeypatch):
    user = make_user(username="minimax-failed")
    model = make_minimax_model(db)
    task = VideoGenerationTask(
        user_id=user.id,
        model_id=model.id,
        generation_type=GenerationType.TEXT_TO_VIDEO,
        prompt="failed task",
        duration=6,
        resolution="768P",
        provider_task_id="failed-task-001",
        status=GenerationStatus.PROCESSING,
        started_at=datetime.now(UTC),
    )
    db.add(task)
    db.commit()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "task_id": "failed-task-001",
                "status": "Fail",
                "base_resp": {"status_code": 0, "status_msg": "success"},
            },
        )

    adapter = adapter_with_transport(model, handler)
    monkeypatch.setattr(
        "app.tasks.generation_tasks.ModelAdapterFactory.create", lambda selected: adapter
    )
    run_generation_task.run(str(task.id))
    db.expire_all()
    saved = db.get(VideoGenerationTask, task.id)
    assert saved.status == GenerationStatus.FAILED
    assert saved.error_code == "MINIMAX_TASK_FAILED"
    assert "minimax-test-secret" not in (saved.error_message or "")


def test_minimax_generation_timeout_does_not_poll_forever(db, make_user, monkeypatch):
    user = make_user(username="minimax-timeout")
    model = make_minimax_model(db)
    model.timeout_seconds = 1
    task = VideoGenerationTask(
        user_id=user.id,
        model_id=model.id,
        generation_type=GenerationType.TEXT_TO_VIDEO,
        prompt="timeout task",
        duration=6,
        resolution="768P",
        provider_task_id="timeout-task-001",
        status=GenerationStatus.PROCESSING,
        started_at=datetime.now(UTC) - timedelta(seconds=2),
    )
    db.add(task)
    db.commit()

    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("expired task must not make another MiniMax request")

    adapter = adapter_with_transport(model, handler)
    monkeypatch.setattr(
        "app.tasks.generation_tasks.ModelAdapterFactory.create", lambda selected: adapter
    )
    run_generation_task.run(str(task.id))
    db.expire_all()
    saved = db.get(VideoGenerationTask, task.id)
    assert saved.status == GenerationStatus.TIMEOUT
    assert saved.error_code == "MINIMAX_TIMEOUT"
