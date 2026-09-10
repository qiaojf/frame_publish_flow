from sqlalchemy import select

from app.core.config import get_settings
from app.core.enums import UserRole
from app.core.logging import logger
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import PublishAccount, PublishPlatform, User, VideoModel


def seed_database() -> None:
    settings = get_settings()
    if not settings.auto_seed:
        return
    if settings.app_env == "production":
        unsafe = {"Admin123!", "User123!", "change-me", "password"}
        configured = {
            settings.default_admin_password.get_secret_value()
            if settings.default_admin_password
            else "",
            settings.default_user_password.get_secret_value()
            if settings.default_user_password
            else "",
        }
        if configured & unsafe:
            raise RuntimeError("生产环境禁止使用示例默认密码")

    with SessionLocal() as db:
        admin = db.scalar(select(User).where(User.username == settings.default_admin_username))
        if admin is None and settings.default_admin_password:
            admin = User(
                username=settings.default_admin_username,
                display_name="系统管理员",
                password_hash=hash_password(settings.default_admin_password.get_secret_value()),
                role=UserRole.ADMIN,
                enabled=True,
            )
            db.add(admin)

        if settings.default_user_username and settings.default_user_password:
            user = db.scalar(select(User).where(User.username == settings.default_user_username))
            if user is None:
                db.add(
                    User(
                        username=settings.default_user_username,
                        display_name="测试用户",
                        password_hash=hash_password(settings.default_user_password.get_secret_value()),
                        role=UserRole.USER,
                        enabled=True,
                    )
                )

        model = db.scalar(select(VideoModel).where(VideoModel.code == "mock-video"))
        if model is None:
            db.add(
                VideoModel(
                    name="Mock Video Model",
                    code="mock-video",
                    provider="Local Mock",
                    adapter_type="mock_video",
                    description="本地联调用视频模型，通过 FFmpeg 生成短视频。",
                    supports_text_to_video=True,
                    supports_image_to_video=True,
                    capabilities={
                        "durations": [2, 5, 10],
                        "aspect_ratios": ["16:9", "9:16", "1:1"],
                        "resolutions": ["720p", "1080p"],
                        "max_images": 1,
                        "max_image_size_mb": settings.upload_max_size_mb,
                    },
                    extra_config={"mock_duration_seconds": 2, "simulate_failure": False},
                    enabled=True,
                )
            )

        platform = db.scalar(select(PublishPlatform).where(PublishPlatform.code == "mock-platform"))
        if platform is None:
            platform = PublishPlatform(
                name="Mock Platform",
                code="mock-platform",
                adapter_type="mock_publish",
                description="本地联调发布平台，不会向任何第三方发送数据。",
                capabilities={
                    "supports_video": True,
                    "supports_cover": True,
                    "requires_account": True,
                    "fields": [
                        {
                            "key": "caption",
                            "label": "平台文案",
                            "type": "textarea",
                            "required": False,
                            "max_length": 1000,
                        }
                    ],
                },
                extra_config={},
                enabled=True,
            )
            db.add(platform)
            db.flush()
        account = db.scalar(
            select(PublishAccount).where(
                PublishAccount.platform_id == platform.id,
                PublishAccount.account_identifier == "mock-default",
            )
        )
        if account is None:
            db.add(
                PublishAccount(
                    platform_id=platform.id,
                    name="默认 Mock 账号",
                    account_identifier="mock-default",
                    extra_config={"simulate_result": "success"},
                    enabled=True,
                )
            )
        db.commit()
        logger.info("database_seed_completed")


if __name__ == "__main__":
    seed_database()
