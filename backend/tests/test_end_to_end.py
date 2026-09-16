import base64
import json

from app.core.enums import UserRole
from app.models import PublishTask, Video
from app.utils.media import VideoMetadata


ONE_PIXEL_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def _login(client, username: str, password: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['data']['access_token']}"}


def _patch_media_tools(monkeypatch) -> None:
    def create_mock_video(self, target, duration=2):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"integration-mp4")
        return target

    def thumbnail(self, source, target):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"integration-jpg")
        return target

    monkeypatch.setattr(
        "app.utils.media.MediaProcessor.create_mock_video",
        create_mock_video,
    )
    monkeypatch.setattr(
        "app.utils.media.MediaProcessor.probe",
        lambda self, source: VideoMetadata(duration=2, width=1280, height=720),
    )
    monkeypatch.setattr("app.utils.media.MediaProcessor.thumbnail", thumbnail)


def test_complete_api_workflow(client, db, make_user, monkeypatch):
    _patch_media_tools(monkeypatch)
    make_user(username="admin", password="Admin123!", role=UserRole.ADMIN)
    admin_headers = _login(client, "admin", "Admin123!")

    me = client.get("/api/v1/auth/me", headers=admin_headers)
    assert me.status_code == 200
    assert me.json()["data"]["role"] == "admin"

    created_user = client.post(
        "/api/v1/admin/users",
        headers=admin_headers,
        json={
            "username": "workflow-user",
            "display_name": "Workflow User",
            "password": "Workflow123!",
            "role": "user",
            "enabled": True,
        },
    )
    assert created_user.status_code == 201, created_user.text
    user_headers = _login(client, "workflow-user", "Workflow123!")
    assert client.get("/api/v1/admin/users", headers=user_headers).status_code == 403

    model_response = client.post(
        "/api/v1/admin/video-models",
        headers=admin_headers,
        json={
            "name": "Workflow Mock Model",
            "code": "workflow-mock-model",
            "provider": "Local Mock",
            "adapter_type": "mock_video",
            "supports_text_to_video": True,
            "supports_image_to_video": True,
            "capabilities": {
                "durations": [2],
                "aspect_ratios": ["16:9"],
                "resolutions": ["720p"],
                "max_images": 1,
            },
            "extra_config": {"mock_duration_seconds": 2},
            "enabled": True,
        },
    )
    assert model_response.status_code == 201, model_response.text
    model_id = model_response.json()["data"]["id"]

    invalid_capability = client.post(
        "/api/v1/generation/tasks",
        headers=user_headers,
        data={"prompt": "非法时长", "model_id": model_id, "duration": "999"},
    )
    assert invalid_capability.status_code == 400

    text_generation = client.post(
        "/api/v1/generation/tasks",
        headers=user_headers,
        data={
            "prompt": "东京雨夜，镜头沿街道前进",
            "model_id": model_id,
            "duration": "2",
            "aspect_ratio": "16:9",
            "resolution": "720p",
        },
    )
    assert text_generation.status_code == 202, text_generation.text
    text_task_id = text_generation.json()["data"]["id"]
    text_task = client.get(
        f"/api/v1/generation/tasks/{text_task_id}",
        headers=user_headers,
    ).json()["data"]
    assert text_task["generation_type"] == "text_to_video"
    assert text_task["status"] == "success"
    text_video_id = text_task["video_id"]

    image_generation = client.post(
        "/api/v1/generation/tasks",
        headers=user_headers,
        data={
            "prompt": "让画面中的光线缓慢移动",
            "model_id": model_id,
            "duration": "2",
            "aspect_ratio": "16:9",
            "resolution": "720p",
        },
        files={"image": ("reference.png", ONE_PIXEL_PNG, "image/png")},
    )
    assert image_generation.status_code == 202, image_generation.text
    image_task_id = image_generation.json()["data"]["id"]
    image_task = client.get(
        f"/api/v1/generation/tasks/{image_task_id}",
        headers=user_headers,
    ).json()["data"]
    assert image_task["generation_type"] == "image_to_video"
    assert image_task["status"] == "success"

    video_detail = client.get(
        f"/api/v1/videos/{text_video_id}",
        headers=user_headers,
    )
    assert video_detail.status_code == 200
    video = video_detail.json()["data"]
    assert video["width"] == 1280
    assert video["height"] == 720
    assert client.get(video["video_url"]).content == b"integration-mp4"
    download = client.get(
        f"/api/v1/videos/{text_video_id}/download",
        headers=user_headers,
    )
    assert download.status_code == 200
    assert download.content == b"integration-mp4"
    assert db.query(Video).count() == 2

    targets = []
    account_ids = []
    for index, mode in enumerate(("success", "success", "failed"), start=1):
        platform_response = client.post(
            "/api/v1/admin/platforms",
            headers=admin_headers,
            json={
                "name": f"Workflow Mock Platform {index}",
                "code": f"workflow-mock-platform-{index}",
                "adapter_type": "mock_publish",
                "capabilities": {
                    "supports_video": True,
                    "supports_cover": True,
                    "requires_account": True,
                    "fields": [],
                },
                "enabled": True,
            },
        )
        assert platform_response.status_code == 201, platform_response.text
        platform_id = platform_response.json()["data"]["id"]
        account_response = client.post(
            "/api/v1/admin/accounts",
            headers=admin_headers,
            json={
                "platform_id": platform_id,
                "name": f"Workflow Account {index}",
                "account_identifier": f"workflow-account-{index}",
                "extra_config": {"simulate_result": mode},
                "enabled": True,
            },
        )
        assert account_response.status_code == 201, account_response.text
        account_id = account_response.json()["data"]["id"]
        account_ids.append(account_id)
        targets.append({"platform_id": platform_id, "account_id": account_id, "overrides": {}})

    public_platforms = client.get("/api/v1/publish/platforms", headers=user_headers)
    assert public_platforms.status_code == 200
    assert len(public_platforms.json()["data"]) == 3

    publish_payload = {
        "video_id": text_video_id,
        "title": "Workflow publish",
        "description": "三个独立平台任务",
        "tags": ["workflow", "mock"],
        "targets": targets,
    }
    publish_headers = {**user_headers, "Idempotency-Key": "workflow-publish-request"}
    publish_response = client.post(
        "/api/v1/publish/tasks",
        headers=publish_headers,
        data={"payload": json.dumps(publish_payload)},
    )
    assert publish_response.status_code == 202, publish_response.text
    task_ids = [item["id"] for item in publish_response.json()["data"]["tasks"]]
    assert len(set(task_ids)) == 3
    assert db.query(PublishTask).count() == 3

    statuses = {
        task_id: client.get(f"/api/v1/publish/tasks/{task_id}", headers=user_headers).json()["data"]
        for task_id in task_ids
    }
    assert sorted(item["status"] for item in statuses.values()) == ["failed", "success", "success"]
    failed_task = next(item for item in statuses.values() if item["status"] == "failed")
    assert failed_task["error_message"]

    idempotent_response = client.post(
        "/api/v1/publish/tasks",
        headers=publish_headers,
        data={"payload": json.dumps(publish_payload)},
    )
    assert idempotent_response.status_code == 202
    assert {item["id"] for item in idempotent_response.json()["data"]["tasks"]} == set(task_ids)
    assert db.query(PublishTask).count() == 3

    failed_account_id = failed_task["account_id"]
    assert failed_account_id == account_ids[2]
    account_update = client.patch(
        f"/api/v1/admin/accounts/{failed_account_id}",
        headers=admin_headers,
        json={"extra_config": {"simulate_result": "success"}},
    )
    assert account_update.status_code == 200
    retry = client.post(
        f"/api/v1/publish/tasks/{failed_task['id']}/retry",
        headers=user_headers,
    )
    assert retry.status_code == 202, retry.text
    retried = client.get(
        f"/api/v1/publish/tasks/{failed_task['id']}",
        headers=user_headers,
    ).json()["data"]
    assert retried["status"] == "success"
    assert retried["retry_count"] == 1
    assert db.query(PublishTask).count() == 3

    image_video_id = image_task["video_id"]
    deleted = client.delete(f"/api/v1/videos/{image_video_id}", headers=user_headers)
    assert deleted.status_code == 204
    assert client.get(f"/api/v1/videos/{image_video_id}", headers=user_headers).status_code == 404

    audit_response = client.get(
        "/api/v1/admin/logs?page=1&page_size=100",
        headers=admin_headers,
    )
    assert audit_response.status_code == 200
    actions = {item["action"] for item in audit_response.json()["items"]}
    assert {
        "auth.login",
        "generation.create",
        "generation.success",
        "video.delete",
        "publish.create",
        "publish.success",
        "publish.failed",
        "publish.retry",
    } <= actions

    cors = client.options(
        "/api/v1/auth/me",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert cors.status_code == 200
    assert cors.headers["access-control-allow-origin"] == "http://localhost:5173"
