from typing import Any

from sqlalchemy import select

from app.core.config import get_settings
from app.core.enums import UserRole
from app.core.logging import logger
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import (
    ModelAccount,
    ModelProvider,
    PublishAccount,
    PublishPlatform,
    User,
    VideoModel,
)


MODEL_PROVIDERS = [
    {
        "name": "Mock Model Provider", "code": "mock", "adapter_family": "mock",
        "auth_type": "none", "default_api_base_url": None, "enabled": True,
    },
    {
        "name": "Google Vertex AI", "code": "google_vertex", "adapter_family": "google",
        "auth_type": "google_adc", "default_api_base_url": "https://aiplatform.googleapis.com",
        "enabled": False,
    },
    {
        "name": "Runway Developer API", "code": "runway", "adapter_family": "runway",
        "auth_type": "api_key", "default_api_base_url": "https://api.dev.runwayml.com",
        "enabled": False,
    },
    {
        "name": "Luma", "code": "luma", "adapter_family": "luma",
        "auth_type": "api_key", "default_api_base_url": "https://api.lumalabs.ai",
        "enabled": False,
    },
    {
        "name": "MiniMax", "code": "minimax", "adapter_family": "minimax",
        "auth_type": "bearer_token", "default_api_base_url": "https://api.minimax.io",
        "provider_capabilities": {
            "video_generation": True, "async_task": True, "file_retrieve": True,
        },
        "extra_config": {"seed_revision": 2}, "enabled": True,
    },
]

MODEL_TEMPLATES: list[dict[str, Any]] = [
    {
        "provider_code": "google_vertex", "name": "Google Veo 3.1", "code": "google-veo-3.1",
        "model_id": "veo-3.1-generate-001", "adapter_type": "google_veo31",
        "capabilities": {
            "text_to_video": True, "image_to_video": True, "supports_first_frame": True,
            "supports_last_frame": True, "supports_reference_image": True, "native_audio": True,
            "duration_mode": "enum", "durations": [4, 6, 8],
            "resolutions": ["720p", "1080p", "4k"], "aspect_ratios": ["16:9", "9:16"],
            "fps": [24], "max_images": 1, "max_image_size_mb": 20,
            "max_outputs_per_request": 4,
        },
    },
    {
        "provider_code": "runway", "name": "Runway Gen-4.5", "code": "runway-gen-4.5",
        "model_id": "gen4.5", "adapter_type": "runway_gen45",
        "capabilities": {
            "text_to_video": True, "image_to_video": True, "supports_first_frame": True,
            "supports_reference_image": True, "duration_mode": "range", "duration_min": 2,
            "duration_max": 10, "resolutions": ["720p"],
            "aspect_ratios_text_to_video": ["16:9", "9:16"],
            "aspect_ratios_image_to_video": ["16:9", "9:16", "1:1", "4:3", "3:4", "21:9"],
            "fps": [24, 25], "max_images": 1,
        },
    },
    {
        "provider_code": "runway", "name": "Seedance 2.5", "code": "runway-seedance-2.5",
        "model_id": "seedance2_5", "adapter_type": "runway_seedance25",
        "capabilities": {
            "text_to_video": True, "image_to_video": True, "supports_first_frame": True,
            "supports_last_frame": True, "supports_reference_image": True,
            "supports_reference_video": True, "supports_reference_audio": True,
            "native_audio": True, "duration_mode": "range", "duration_min": 4,
            "duration_max": 30, "resolutions": ["480p", "720p", "1080p"],
            "aspect_ratios": ["16:9", "9:16", "1:1", "4:3", "3:4", "21:9"],
            "max_images": 30, "max_reference_videos": 10, "max_reference_audios": 10,
        },
    },
    {
        "provider_code": "luma", "name": "Luma Ray 3.2", "code": "luma-ray-3.2",
        "model_id": "ray-3.2", "adapter_type": "luma_ray32",
        "capabilities": {
            "text_to_video": True, "image_to_video": True, "supports_first_frame": True,
            "supports_last_frame": True, "supports_reference_image": True, "supports_loop": True,
            "supports_hdr": True, "duration_mode": "enum", "durations": [5, 10],
            "resolutions": ["360p", "540p", "720p", "1080p"],
            "aspect_ratios": ["9:16", "3:4", "1:1", "4:3", "16:9", "21:9"],
        },
    },
    {
        "provider_code": "minimax", "name": "MiniMax Hailuo 2.3", "code": "minimax_hailuo_2_3",
        "model_id": "MiniMax-Hailuo-2.3", "adapter_type": "minimax_hailuo23",
        "capabilities": {
            "text_to_video": True, "image_to_video": True, "supports_first_frame": True,
            "prompt": {
                "required_for_text_to_video": True,
                "required_for_image_to_video": False,
                "max_length": 2000,
            },
            "prompt_optimizer": {"supported": True, "default": True},
            "fast_pretreatment": {"supported": True, "default": False},
            "duration_mode": "enum", "durations": [6, 10],
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
            "camera_commands_supported": True,
            "callback_supported": True,
            "parameter_combination_error_code": "INVALID_MODEL_PARAMETER_COMBINATION",
            "parameter_combination_error_message": (
                "MiniMax Hailuo 2.3 does not support 1080P for 10-second generation."
            ),
        },
        "request_defaults": {
            "duration": 6, "resolution": "768P",
            "prompt_optimizer": True, "fast_pretreatment": False,
        },
        "extra_config": {"seed_revision": 2},
        "timeout_seconds": 900,
        "enabled": True,
        "description": "MiniMax 官方 Hailuo 2.3 文生视频/图生视频模型。",
    },
]

PUBLISH_PLATFORMS: list[dict[str, Any]] = [
    {
        "name": "X", "code": "x", "adapter_type": "x_v2", "api_base_url": "https://api.x.com",
        "auth_type": "oauth2_pkce", "enabled": False,
        "capabilities": {"public_publish": True, "supports_text": True, "supports_image": True,
                         "supports_video": True, "supports_title": False, "supports_description": False,
                         "supports_tags": False, "requires_public_media_url": False, "requires_oauth": True},
    },
    {
        "name": "Instagram", "code": "instagram", "adapter_type": "instagram_graph",
        "api_base_url": "https://graph.instagram.com", "api_version": "v26.0",
        "auth_type": "oauth2", "enabled": False,
        "capabilities": {
            "public_publish": True, "supports_image": False, "supports_video": True,
            "supports_reel": True, "supports_story": False, "supports_carousel": False,
            "supports_caption": True, "requires_public_media_url": True, "requires_oauth": True,
            "fields": [
                {"key": "video_url", "label": "公网视频 URL", "type": "text",
                 "required": True, "placeholder": "https://example.com/video.mp4"},
                {"key": "caption", "label": "Instagram 文案", "type": "textarea",
                 "required": False, "max_length": 2200},
                {"key": "share_to_feed", "label": "同时分享到动态", "type": "boolean",
                 "required": False, "default": True},
            ],
        },
        "extra_config": {
            "poll_interval_seconds": 5,
            "processing_timeout_seconds": 300,
            "http_timeout_seconds": 30,
            "require_https_video_url": True,
            "seed_revision": 1,
        },
    },
    {
        "name": "YouTube", "code": "youtube", "adapter_type": "youtube_data_api_v3",
        "api_base_url": "https://www.googleapis.com/youtube/v3", "auth_type": "oauth2", "enabled": False,
        "capabilities": {"public_publish": True, "supports_video": True, "supports_title": True,
                         "supports_description": True, "supports_tags": True, "supports_privacy": True,
                         "supports_schedule": True, "supports_thumbnail": True, "supports_made_for_kids": True,
                         "supports_synthetic_media_disclosure": True, "requires_public_media_url": False,
                         "requires_oauth": True},
    },
    {
        "name": "Facebook", "code": "facebook", "adapter_type": "facebook_graph",
        "api_base_url": "https://graph.facebook.com", "auth_type": "oauth2", "enabled": False,
        "capabilities": {"public_publish": True, "supports_text": True, "supports_image": True,
                         "supports_video": True, "supports_reel": True, "supports_title": True,
                         "supports_description": True, "supports_schedule": True,
                         "requires_public_media_url": False, "requires_oauth": True,
                         "extra": {"reel": {"aspect_ratios": ["9:16"], "duration_min": 4,
                                               "duration_max": 60, "min_resolution": "540x960"}}},
    },
]


def _seed_users(db: Any, settings: Any) -> None:
    admin = db.scalar(select(User).where(User.username == settings.default_admin_username))
    if admin is None and settings.default_admin_password:
        db.add(User(username=settings.default_admin_username, display_name="系统管理员",
                    password_hash=hash_password(settings.default_admin_password.get_secret_value()),
                    role=UserRole.ADMIN, enabled=True))
    if settings.default_user_username and settings.default_user_password:
        user = db.scalar(select(User).where(User.username == settings.default_user_username))
        if user is None:
            db.add(User(username=settings.default_user_username, display_name="测试用户",
                        password_hash=hash_password(settings.default_user_password.get_secret_value()),
                        role=UserRole.USER, enabled=True))


def _seed_models(db: Any, settings: Any) -> None:
    providers: dict[str, ModelProvider] = {}
    for values in MODEL_PROVIDERS:
        provider = db.scalar(select(ModelProvider).where(ModelProvider.code == values["code"]))
        if provider is None:
            provider_values = dict(values)
            if values["code"] == "minimax":
                provider_values["default_api_base_url"] = settings.minimax_api_base_url
            provider_values.setdefault("provider_capabilities", {})
            provider_values.setdefault("extra_config", {})
            provider_values.setdefault("default_api_version", None)
            provider = ModelProvider(**provider_values)
            db.add(provider)
            db.flush()
        elif values["code"] == "minimax" and int((provider.extra_config or {}).get("seed_revision", 0)) < 2:
            provider.name = values["name"]
            provider.adapter_family = values["adapter_family"]
            provider.default_api_base_url = settings.minimax_api_base_url
            provider.auth_type = values["auth_type"]
            provider.provider_capabilities = values["provider_capabilities"]
            provider.extra_config = {**(provider.extra_config or {}), **values["extra_config"]}
            provider.enabled = True
        providers[provider.code] = provider

    accounts: dict[str, ModelAccount] = {}
    for code, provider in providers.items():
        identifier = f"{code}-default"
        account = db.scalar(
            select(ModelAccount).where(
                ModelAccount.provider_id == provider.id,
                ModelAccount.account_identifier == identifier,
            )
        )
        if account is None:
            account = ModelAccount(
                provider_id=provider.id,
                name=(
                    "Mock Model Account"
                    if code == "mock"
                    else "MiniMax PoC Account"
                    if code == "minimax"
                    else f"{provider.name} Template Account"
                ),
                account_identifier=identifier,
                api_version="v1" if code == "minimax" else None,
                credential_extra={},
                extra_config={"seed_revision": 2} if code == "minimax" else {},
                enabled=code in {"mock", "minimax"},
            )
            db.add(account)
            db.flush()
        elif code == "minimax" and int((account.extra_config or {}).get("seed_revision", 0)) < 2:
            account.name = "MiniMax PoC Account"
            account.api_version = "v1"
            account.extra_config = {**(account.extra_config or {}), "seed_revision": 2}
            account.enabled = True
        accounts[code] = account

    mock = db.scalar(select(VideoModel).where(VideoModel.code == "mock-video"))
    if mock is None:
        db.add(VideoModel(
            model_account_id=accounts["mock"].id, name="Mock Video Model", code="mock-video",
            model_id="mock-video", adapter_type="mock_video",
            description="本地联调用视频模型，通过 FFmpeg 生成短视频。",
            supports_text_to_video=True, supports_image_to_video=True,
            capabilities={"text_to_video": True, "image_to_video": True, "duration_mode": "enum",
                          "durations": [2, 5, 10], "aspect_ratios": ["16:9", "9:16", "1:1"],
                          "resolutions": ["720p", "1080p"], "max_images": 1,
                          "max_image_size_mb": settings.upload_max_size_mb},
            request_defaults={"duration": 2, "aspect_ratio": "16:9", "resolution": "720p"},
            extra_config={"mock_duration_seconds": 2, "simulate_failure": False}, enabled=True,
        ))
    elif mock.model_account_id != accounts["mock"].id:
        # Migrations preserve legacy credentials in their own account; the built-in
        # mock model is intentionally attached to the credential-free mock account.
        mock.model_account_id = accounts["mock"].id
    for template in MODEL_TEMPLATES:
        values = dict(template)
        provider_code = values.pop("provider_code")
        capabilities = values.pop("capabilities")
        request_defaults = values.pop("request_defaults", {})
        extra_config = values.pop("extra_config", {})
        timeout_seconds = values.pop("timeout_seconds", 300)
        description = values.pop(
            "description", "真实模型配置模板；填写凭证并通过连接测试后再启用。"
        )
        enabled = values.pop("enabled", False)
        model = db.scalar(select(VideoModel).where(VideoModel.code == template["code"]))
        if model is None and template["adapter_type"] == "minimax_hailuo23":
            model = db.scalar(
                select(VideoModel).where(VideoModel.code == "minimax-hailuo-2.3")
            )
        if model is None:
            db.add(VideoModel(
                model_account_id=accounts[provider_code].id,
                **values,
                supports_text_to_video=True,
                supports_image_to_video=True,
                capabilities=capabilities,
                request_defaults=request_defaults,
                extra_config=extra_config,
                timeout_seconds=timeout_seconds,
                description=description,
                enabled=enabled,
            ))
        elif template["adapter_type"] == "minimax_hailuo23" and int(
            (model.extra_config or {}).get("seed_revision", 0)
        ) < 2:
            for key, value in values.items():
                setattr(model, key, value)
            model.model_account_id = accounts[provider_code].id
            model.supports_text_to_video = True
            model.supports_image_to_video = True
            model.capabilities = {**(model.capabilities or {}), **capabilities}
            model.request_defaults = {**(model.request_defaults or {}), **request_defaults}
            model.extra_config = {**(model.extra_config or {}), **extra_config}
            model.timeout_seconds = timeout_seconds
            model.description = description
            model.enabled = enabled


def _seed_publish_platforms(db: Any) -> None:
    mock = db.scalar(select(PublishPlatform).where(PublishPlatform.code == "mock-platform"))
    if mock is None:
        mock = PublishPlatform(
            name="Mock Platform", code="mock-platform", adapter_type="mock_publish", auth_type="none",
            description="本地联调发布平台，不会向任何第三方发送数据。",
            capabilities={"public_publish": False, "supports_video": True, "supports_cover": True,
                          "requires_account": True,
                          "fields": [{"key": "caption", "label": "平台文案", "type": "textarea",
                                      "required": False, "max_length": 1000}]},
            extra_config={}, enabled=True,
        )
        db.add(mock)
        db.flush()
    account = db.scalar(select(PublishAccount).where(
        PublishAccount.platform_id == mock.id, PublishAccount.account_identifier == "mock-default"
    ))
    if account is None:
        db.add(PublishAccount(platform_id=mock.id, name="默认 Mock 账号",
                              account_identifier="mock-default", authorized_scopes=[],
                              extra_config={"simulate_result": "success"}, enabled=True))
    for values in PUBLISH_PLATFORMS:
        platform = db.scalar(select(PublishPlatform).where(PublishPlatform.code == values["code"]))
        if platform is None:
            platform_values = dict(values)
            platform_values.setdefault("api_version", None)
            platform_values.setdefault("extra_config", {})
            db.add(PublishPlatform(
                **platform_values,
                description="真实平台模板；完成 OAuth 连接和验证后再启用。",
            ))
        elif values["code"] == "instagram" and int(
            (platform.extra_config or {}).get("seed_revision", 0)
        ) < int(values["extra_config"]["seed_revision"]):
            platform.adapter_type = values["adapter_type"]
            platform.api_base_url = platform.api_base_url or values["api_base_url"]
            platform.api_version = platform.api_version or values["api_version"]
            platform.auth_type = values["auth_type"]
            platform.capabilities = {**(platform.capabilities or {}), **values["capabilities"]}
            platform.extra_config = {
                **values["extra_config"],
                **(platform.extra_config or {}),
                "seed_revision": values["extra_config"]["seed_revision"],
            }


def seed_database() -> None:
    settings = get_settings()
    if not settings.auto_seed:
        return
    if settings.app_env == "production":
        unsafe = {"Admin123!", "User123!", "change-me", "password"}
        configured = {
            settings.default_admin_password.get_secret_value() if settings.default_admin_password else "",
            settings.default_user_password.get_secret_value() if settings.default_user_password else "",
        }
        if configured & unsafe:
            raise RuntimeError("生产环境禁止使用示例默认密码")
    with SessionLocal() as db:
        _seed_users(db, settings)
        _seed_models(db, settings)
        _seed_publish_platforms(db)
        db.commit()
        logger.info("database_seed_completed")


if __name__ == "__main__":
    seed_database()
