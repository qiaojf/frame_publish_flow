from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: Literal["development", "test", "production"] = "development"
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    public_base_url: str = "http://127.0.0.1:8000"
    database_url: str
    redis_url: str = "redis://127.0.0.1:6379/0"
    celery_broker_url: str = "redis://127.0.0.1:6379/0"
    celery_result_backend: str = "redis://127.0.0.1:6379/1"
    celery_task_always_eager: bool = False
    celery_max_retries: int = 3
    jwt_secret_key: SecretStr
    jwt_expire_minutes: int = 120
    secret_encryption_key: SecretStr | None = None
    storage_type: Literal["local", "s3", "minio"] = "local"
    storage_path: Path = Path("../storage")
    upload_max_size_mb: int = 10
    ffmpeg_binary: str = "ffmpeg"
    ffprobe_binary: str = "ffprobe"
    generation_poll_interval: int = 2
    generation_timeout: int = 120
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    auto_seed: bool = True
    default_admin_username: str = "admin"
    default_admin_password: SecretStr | None = None
    default_user_username: str | None = "user"
    default_user_password: SecretStr | None = None

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def upload_max_bytes(self) -> int:
        return self.upload_max_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
