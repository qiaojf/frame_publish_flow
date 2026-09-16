import json

import pytest

from app.adapters.publishing.facebook import FacebookPublishAdapter
from app.adapters.publishing.factory import PublishAdapterFactory
from app.adapters.publishing.instagram import InstagramPublishAdapter
from app.adapters.publishing.x import XPublishAdapter
from app.adapters.publishing.youtube import YouTubePublishAdapter
from app.adapters.video_models.factory import ModelAdapterFactory
from app.adapters.video_models.google_veo31 import GoogleVeo31Adapter
from app.adapters.video_models.luma_ray32 import LumaRay32Adapter
from app.adapters.video_models.minimax_hailuo23 import MiniMaxHailuo23Adapter
from app.adapters.video_models.runway_gen45 import RunwayGen45Adapter
from app.adapters.video_models.runway_seedance25 import RunwaySeedance25Adapter
from app.core.enums import UserRole
from app.core.config import get_settings
from app.db.init_db import _seed_models, _seed_publish_platforms
from app.models import (
    ModelAccount,
    ModelProvider,
    PublishPlatform,
    PublishTask,
    VideoModel,
)


@pytest.fixture
def no_queue(monkeypatch):
    monkeypatch.setattr("app.tasks.generation_tasks.run_generation_task.delay", lambda task_id: None)


@pytest.fixture
def no_publish_queue(monkeypatch):
    monkeypatch.setattr("app.tasks.publish_tasks.run_publish_task.delay", lambda task_id: None)


def test_model_provider_account_model_crud_and_masking(client, make_user, auth_headers):
    admin = make_user(username="admin", role=UserRole.ADMIN)
    user = make_user(username="normal")
    headers = auth_headers(admin)
    provider_response = client.post(
        "/api/v1/admin/model-providers",
        headers=headers,
        json={
            "name": "Runway Developer API",
            "code": "runway-test",
            "adapter_family": "runway",
            "default_api_base_url": "https://provider.invalid",
            "auth_type": "api_key",
            "enabled": True,
        },
    )
    assert provider_response.status_code == 201
    provider_id = provider_response.json()["data"]["id"]
    account_response = client.post(
        "/api/v1/admin/model-accounts",
        headers=headers,
        json={
            "provider_id": provider_id,
            "name": "Production",
            "api_key": "super-secret-model-key",
            "extra_config": {"operation_paths": {"status": "/tasks/{task_id}"}},
            "enabled": True,
        },
    )
    assert account_response.status_code == 201
    assert "super-secret-model-key" not in account_response.text
    assert account_response.json()["data"]["api_key_masked"]
    account_id = account_response.json()["data"]["id"]
    model_response = client.post(
        "/api/v1/admin/video-models",
        headers=headers,
        json={
            "model_account_id": account_id,
            "name": "Gen-4.5",
            "code": "gen45-test",
            "model_id": "gen4.5",
            "adapter_type": "runway_gen45",
            "supports_text_to_video": True,
            "supports_image_to_video": True,
            "capabilities": {"duration_mode": "range", "duration_min": 2, "duration_max": 10},
            "request_defaults": {"duration": 5},
            "enabled": True,
        },
    )
    assert model_response.status_code == 201
    body = model_response.json()["data"]
    assert body["model_account_id"] == account_id
    assert body["provider"] == "Runway Developer API"
    assert body["request_defaults"] == {"duration": 5}
    assert "super-secret-model-key" not in model_response.text

    account_test = client.post(
        f"/api/v1/admin/model-accounts/{account_id}/test", headers=headers
    )
    assert account_test.status_code == 200
    assert account_test.json()["data"]["configured"] is True
    model_test = client.post(
        f"/api/v1/admin/video-models/{body['id']}/test", headers=headers
    )
    assert model_test.status_code == 200
    assert model_test.json()["data"]["configured"] is True

    public = client.get("/api/v1/video-models", headers=auth_headers(user))
    item = next(item for item in public.json()["data"] if item["id"] == body["id"])
    assert item["adapter_type"] is None
    assert item["api_key_masked"] is None
    assert item["provider_code"] == "runway-test"


@pytest.mark.parametrize(
    ("adapter_type", "expected"),
    [
        ("google_veo31", GoogleVeo31Adapter),
        ("runway_gen45", RunwayGen45Adapter),
        ("runway_seedance25", RunwaySeedance25Adapter),
        ("luma_ray32", LumaRay32Adapter),
        ("minimax_hailuo23", MiniMaxHailuo23Adapter),
    ],
)
def test_real_model_adapters_load_without_credentials(db, adapter_type, expected):
    provider = ModelProvider(
        name="Disabled Provider", code=f"provider-{adapter_type}", adapter_family="test",
        auth_type="api_key", provider_capabilities={}, extra_config={}, enabled=False,
    )
    db.add(provider)
    db.flush()
    account = ModelAccount(
        provider_id=provider.id, name="Template", credential_extra={}, extra_config={}, enabled=False
    )
    db.add(account)
    db.flush()
    model = VideoModel(
        model_account_id=account.id, name=adapter_type, code=f"model-{adapter_type}",
        model_id="template", adapter_type=adapter_type, supports_text_to_video=True,
        supports_image_to_video=True, capabilities={}, request_defaults={}, extra_config={}, enabled=False,
    )
    db.add(model)
    db.commit()
    assert isinstance(ModelAdapterFactory.create(model), expected)


@pytest.mark.parametrize(
    ("adapter_type", "expected"),
    [
        ("x_v2", XPublishAdapter),
        ("instagram_graph", InstagramPublishAdapter),
        ("youtube_data_api_v3", YouTubePublishAdapter),
        ("facebook_graph", FacebookPublishAdapter),
    ],
)
def test_public_publish_adapters_are_registered(make_platform, adapter_type, expected):
    platform, account = make_platform()
    platform.adapter_type = adapter_type
    assert isinstance(PublishAdapterFactory.create(platform, account), expected)


def test_resolution_duration_matrix_is_enforced(
    client, db, make_user, make_model, auth_headers, no_queue
):
    user = make_user()
    model = make_model()
    model.capabilities = {
        "duration_mode": "enum",
        "durations": [6, 10],
        "resolutions": ["768p", "1080p"],
        "resolution_duration_matrix": {"768p": [6, 10], "1080p": [6]},
    }
    db.commit()
    rejected = client.post(
        "/api/v1/generation/tasks",
        headers=auth_headers(user),
        data={"prompt": "矩阵校验", "model_id": str(model.id), "duration": 10, "resolution": "1080p"},
    )
    assert rejected.status_code == 400
    assert rejected.json()["error_code"] == "INVALID_RESOLUTION_DURATION"


def test_v2_common_publish_payload_is_persisted(
    client, db, make_user, make_video, make_platform, auth_headers, no_publish_queue
):
    user = make_user()
    video = make_video(user)
    platform, account = make_platform()
    platform.capabilities = {"supports_video": True, "supports_reel": True}
    db.commit()
    response = client.post(
        "/api/v1/publish/tasks",
        headers=auth_headers(user),
        data={
            "payload": json.dumps({
                "video_id": str(video.id),
                "common": {
                    "title": "统一标题", "content": "正文", "description": "描述", "tags": ["AI"]
                },
                "targets": [{
                    "platform_id": str(platform.id), "account_id": str(account.id),
                    "publish_type": "reel", "overrides": {"caption": "平台文案"},
                }],
            })
        },
    )
    assert response.status_code == 202
    task = db.query(PublishTask).one()
    assert task.publish_type == "reel"
    assert task.description == "描述"
    assert task.common_payload["content"] == "正文"
    assert task.platform_payload["caption"] == "平台文案"


def test_v2_seed_enables_mock_and_minimax_model_integrations(db):
    _seed_models(db, get_settings())
    _seed_publish_platforms(db)
    db.commit()
    models = db.query(VideoModel).all()
    assert {model.adapter_type for model in models if not model.enabled} == {
        "google_veo31", "runway_gen45", "runway_seedance25", "luma_ray32",
    }
    assert {model.code for model in models if model.enabled} == {
        "mock-video", "minimax_hailuo_2_3"
    }
    platforms = db.query(PublishPlatform).all()
    assert {platform.code for platform in platforms if not platform.enabled} == {
        "x", "instagram", "youtube", "facebook",
    }
    assert {platform.code for platform in platforms if platform.enabled} == {"mock-platform"}
