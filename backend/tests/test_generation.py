import asyncio
import io
from pathlib import Path

import pytest

from app.adapters.video_models.base import GeneratedVideo, GenerationRequest
from app.adapters.video_models.mock import MockVideoModelAdapter
from app.core.enums import GenerationStatus, GenerationType
from app.models import Video, VideoGenerationTask
from app.tasks.generation_tasks import run_generation_task
from app.utils.media import VideoMetadata


@pytest.fixture
def no_queue(monkeypatch):
    monkeypatch.setattr("app.tasks.generation_tasks.run_generation_task.delay", lambda task_id: None)


def test_text_and_image_generation_detection(client, make_user, make_model, auth_headers, no_queue):
    user = make_user()
    model = make_model()
    text = client.post(
        "/api/v1/generation/tasks",
        headers=auth_headers(user),
        data={"prompt": "海边日落", "model_id": str(model.id), "duration": "2", "aspect_ratio": "16:9", "resolution": "720p"},
    )
    assert text.status_code == 202
    assert text.json()["data"]["generation_type"] == "text_to_video"

    image = client.post(
        "/api/v1/generation/tasks",
        headers=auth_headers(user),
        data={"prompt": "镜头向前移动", "model_id": str(model.id), "duration": "2"},
        files={"image": ("reference.png", io.BytesIO(b"fake-png"), "image/png")},
    )
    assert image.status_code == 202
    assert image.json()["data"]["generation_type"] == "image_to_video"


def test_generation_validation(client, make_user, make_model, auth_headers, no_queue):
    user = make_user()
    text_only = make_model(image=False)
    empty = client.post(
        "/api/v1/generation/tasks",
        headers=auth_headers(user),
        data={"prompt": " ", "model_id": str(text_only.id)},
    )
    assert empty.status_code == 400
    unsupported = client.post(
        "/api/v1/generation/tasks",
        headers=auth_headers(user),
        data={"prompt": "动起来", "model_id": str(text_only.id)},
        files={"image": ("image.png", b"png", "image/png")},
    )
    assert unsupported.status_code == 400
    invalid_duration = client.post(
        "/api/v1/generation/tasks",
        headers=auth_headers(user),
        data={"prompt": "测试", "model_id": str(text_only.id), "duration": "99"},
    )
    assert invalid_duration.status_code == 400
    disabled = make_model(enabled=False)
    disabled_response = client.post(
        "/api/v1/generation/tasks",
        headers=auth_headers(user),
        data={"prompt": "测试", "model_id": str(disabled.id)},
    )
    assert disabled_response.status_code == 400


def test_image_type_and_size_validation(client, make_user, make_model, auth_headers, no_queue):
    user = make_user()
    model = make_model()
    invalid_type = client.post(
        "/api/v1/generation/tasks",
        headers=auth_headers(user),
        data={"prompt": "非法图片", "model_id": str(model.id)},
        files={"image": ("reference.gif", b"GIF89a", "image/gif")},
    )
    assert invalid_type.status_code == 400
    assert invalid_type.json()["error_code"] == "INVALID_IMAGE_TYPE"

    too_large = client.post(
        "/api/v1/generation/tasks",
        headers=auth_headers(user),
        data={"prompt": "超大图片", "model_id": str(model.id)},
        files={"image": ("reference.png", b"x" * (10 * 1024 * 1024 + 1), "image/png")},
    )
    assert too_large.status_code == 400
    assert too_large.json()["error_code"] == "IMAGE_TOO_LARGE"


def test_generation_queue_failure_is_reported(
    client,
    db,
    make_user,
    make_model,
    auth_headers,
    monkeypatch,
):
    user = make_user()
    model = make_model()

    def unavailable(task_id):
        raise ConnectionError("redis unavailable")

    monkeypatch.setattr("app.tasks.generation_tasks.run_generation_task.delay", unavailable)
    response = client.post(
        "/api/v1/generation/tasks",
        headers=auth_headers(user),
        data={"prompt": "队列失败", "model_id": str(model.id)},
    )
    assert response.status_code == 503
    assert response.json()["error_code"] == "QUEUE_UNAVAILABLE"
    task = db.query(VideoGenerationTask).one()
    db.refresh(task)
    assert task.status == GenerationStatus.FAILED


def test_generation_task_owner_permission(client, make_user, make_model, auth_headers, no_queue):
    owner = make_user(username="owner")
    other = make_user(username="other")
    model = make_model()
    created = client.post(
        "/api/v1/generation/tasks",
        headers=auth_headers(owner),
        data={"prompt": "所有者任务", "model_id": str(model.id)},
    )
    task_id = created.json()["data"]["id"]
    forbidden = client.get(f"/api/v1/generation/tasks/{task_id}", headers=auth_headers(other))
    assert forbidden.status_code == 403


def test_generation_worker_creates_video(db, make_user, make_model, monkeypatch, tmp_path):
    user = make_user()
    model = make_model()
    task = VideoGenerationTask(
        user_id=user.id,
        model_id=model.id,
        generation_type=GenerationType.TEXT_TO_VIDEO,
        prompt="Worker 生成视频",
        status=GenerationStatus.PENDING,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    class FakeAdapter:
        async def create_text_to_video(self, request):
            return "provider-1"

        async def create_image_to_video(self, request):
            return "provider-1"

        async def get_task_status(self, provider_task_id):
            return "success"

        async def get_result(self, provider_task_id, work_dir: Path):
            path = work_dir / "video.mp4"
            path.write_bytes(b"video")
            return GeneratedVideo(path, provider_task_id)

    monkeypatch.setattr("app.tasks.generation_tasks.ModelAdapterFactory.create", lambda model: FakeAdapter())
    monkeypatch.setattr("app.tasks.generation_tasks.MediaProcessor.probe", lambda self, path: VideoMetadata(2, 1280, 720))

    def fake_thumbnail(self, source, target):
        target.write_bytes(b"jpg")
        return target

    monkeypatch.setattr("app.tasks.generation_tasks.MediaProcessor.thumbnail", fake_thumbnail)
    run_generation_task.run(str(task.id))
    db.expire_all()
    saved_task = db.get(VideoGenerationTask, task.id)
    assert saved_task.status == GenerationStatus.SUCCESS
    assert db.query(Video).filter(Video.generation_task_id == task.id).count() == 1


def test_mock_generation_worker_can_fail(db, make_user, make_model):
    user = make_user()
    model = make_model()
    model.extra_config = {"simulate_failure": True}
    task = VideoGenerationTask(
        user_id=user.id,
        model_id=model.id,
        generation_type=GenerationType.TEXT_TO_VIDEO,
        prompt="模拟失败",
        status=GenerationStatus.PENDING,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    run_generation_task.run(str(task.id))

    db.expire_all()
    failed_task = db.get(VideoGenerationTask, task.id)
    assert failed_task.status == GenerationStatus.FAILED
    assert failed_task.error_code == "GENERATION_FAILED"
    assert db.query(Video).filter(Video.generation_task_id == task.id).count() == 0


def test_mock_video_adapter_success(monkeypatch, tmp_path):
    adapter = MockVideoModelAdapter({"mock_duration_seconds": 2})
    request = GenerationRequest(
        prompt="Mock 成功",
        duration=2,
        aspect_ratio="16:9",
        resolution="720p",
    )
    provider_id = asyncio.run(adapter.create_text_to_video(request))
    assert asyncio.run(adapter.get_task_status(provider_id)) == "success"

    def fake_create(target: Path, duration: int):
        target.write_bytes(b"mock-video")
        return target

    monkeypatch.setattr(adapter.media, "create_mock_video", fake_create)
    result = asyncio.run(adapter.get_result(provider_id, tmp_path))
    assert result.local_path.read_bytes() == b"mock-video"
