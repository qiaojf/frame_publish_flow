import os
import uuid
from pathlib import Path
from typing import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

TEST_ROOT = Path(__file__).resolve().parent
DB_PATH = TEST_ROOT / "frameflow-test.db"
STORAGE_PATH = TEST_ROOT / "test-storage"
os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{DB_PATH.as_posix()}"
os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key-with-at-least-32-characters"
os.environ["SECRET_ENCRYPTION_KEY"] = "test-encryption-key-with-at-least-32-characters"
os.environ["AUTO_SEED"] = "false"
os.environ["CELERY_TASK_ALWAYS_EAGER"] = "true"
os.environ["CELERY_BROKER_URL"] = "memory://"
os.environ["CELERY_RESULT_BACKEND"] = "cache+memory://"
os.environ["STORAGE_PATH"] = str(STORAGE_PATH)

from app.core.enums import GenerationStatus, GenerationType, UserRole  # noqa: E402
from app.core.security import create_access_token, hash_password  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import (  # noqa: E402
    PublishAccount,
    PublishPlatform,
    User,
    Video,
    VideoGenerationTask,
    VideoModel,
)

Base.metadata.create_all(engine)


@pytest.fixture(autouse=True)
def clean_database() -> None:
    with engine.begin() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
        for table_name in [
            "audit_logs",
            "publish_tasks",
            "videos",
            "video_generation_tasks",
            "publish_accounts",
            "publish_platforms",
            "video_models",
            "users",
        ]:
            connection.exec_driver_sql(f"DELETE FROM {table_name}")
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")
    STORAGE_PATH.mkdir(parents=True, exist_ok=True)


@pytest.fixture
def db() -> Session:
    with SessionLocal() as session:
        yield session


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def make_user(db: Session) -> Callable[..., User]:
    def factory(
        username: str = "user",
        password: str = "User123!",
        role: UserRole = UserRole.USER,
        enabled: bool = True,
    ) -> User:
        user = User(
            username=username,
            display_name=username.title(),
            password_hash=hash_password(password),
            role=role,
            enabled=enabled,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    return factory


@pytest.fixture
def auth_headers() -> Callable[[User], dict[str, str]]:
    def factory(user: User) -> dict[str, str]:
        token = create_access_token(str(user.id), user.role.value)
        return {"Authorization": f"Bearer {token}"}

    return factory


@pytest.fixture
def make_model(db: Session) -> Callable[..., VideoModel]:
    def factory(
        *,
        enabled: bool = True,
        text: bool = True,
        image: bool = True,
        extra_config: dict | None = None,
    ) -> VideoModel:
        model = VideoModel(
            name=f"Model {uuid.uuid4().hex[:6]}",
            code=f"model-{uuid.uuid4().hex}",
            provider="Test",
            adapter_type="mock_video",
            supports_text_to_video=text,
            supports_image_to_video=image,
            capabilities={
                "durations": [2, 5],
                "aspect_ratios": ["16:9", "9:16"],
                "resolutions": ["720p"],
                "max_images": 1,
            },
            extra_config=extra_config or {},
            enabled=enabled,
        )
        db.add(model)
        db.commit()
        db.refresh(model)
        return model

    return factory


@pytest.fixture
def make_platform(db: Session) -> Callable[..., tuple[PublishPlatform, PublishAccount]]:
    def factory(simulate_result: str = "success") -> tuple[PublishPlatform, PublishAccount]:
        platform = PublishPlatform(
            name=f"Platform {uuid.uuid4().hex[:6]}",
            code=f"platform-{uuid.uuid4().hex}",
            adapter_type="mock_publish",
            capabilities={"supports_video": True, "fields": []},
            extra_config={},
            enabled=True,
        )
        db.add(platform)
        db.flush()
        account = PublishAccount(
            platform_id=platform.id,
            name=f"Account {uuid.uuid4().hex[:6]}",
            account_identifier=uuid.uuid4().hex,
            extra_config={"simulate_result": simulate_result},
            enabled=True,
        )
        db.add(account)
        db.commit()
        db.refresh(platform)
        db.refresh(account)
        return platform, account

    return factory


@pytest.fixture
def make_video(db: Session, make_user, make_model) -> Callable[..., Video]:
    def factory(user: User | None = None, model: VideoModel | None = None) -> Video:
        owner = user or make_user(username=f"user-{uuid.uuid4().hex[:6]}")
        selected_model = model or make_model()
        generation = VideoGenerationTask(
            user_id=owner.id,
            model_id=selected_model.id,
            generation_type=GenerationType.TEXT_TO_VIDEO,
            prompt="测试视频",
            status=GenerationStatus.SUCCESS,
        )
        db.add(generation)
        db.flush()
        key = f"videos/{owner.id}/{generation.id}.mp4"
        path = STORAGE_PATH / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"test-video-content")
        video = Video(
            owner_id=owner.id,
            generation_task_id=generation.id,
            title="测试视频",
            description="测试视频",
            video_url=f"/storage/{key}",
            storage_key=key,
            file_size=path.stat().st_size,
            mime_type="video/mp4",
        )
        db.add(video)
        db.flush()
        generation.result_video_id = video.id
        db.commit()
        db.refresh(video)
        return video

    return factory
