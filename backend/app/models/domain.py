import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.core.enums import AuditResult, GenerationStatus, GenerationType, PublishStatus, UserRole
from app.db.base import Base

JSON_TYPE = JSON().with_variant(JSONB(), "postgresql")


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class User(TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_role", "role"),
        Index("ix_users_enabled", "enabled"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(120))
    email: Mapped[str | None] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, values_callable=lambda values: [item.value for item in values], native_enum=False),
        default=UserRole.USER,
        nullable=False,
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class VideoModel(TimestampMixin, Base):
    __tablename__ = "video_models"
    __table_args__ = (Index("ix_video_models_enabled", "enabled"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    code: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    provider: Mapped[str] = mapped_column(String(80), nullable=False)
    adapter_type: Mapped[str] = mapped_column(String(80), nullable=False)
    api_base_url: Mapped[str | None] = mapped_column(String(500))
    api_key_encrypted: Mapped[str | None] = mapped_column(Text)
    model_id: Mapped[str | None] = mapped_column(String(200))
    supports_text_to_video: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    supports_image_to_video: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    capabilities: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    extra_config: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=300, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class VideoGenerationTask(TimestampMixin, Base):
    __tablename__ = "video_generation_tasks"
    __table_args__ = (
        Index("ix_generation_tasks_user_id", "user_id"),
        Index("ix_generation_tasks_model_id", "model_id"),
        Index("ix_generation_tasks_status", "status"),
        Index("ix_generation_tasks_created_at", "created_at"),
        Index("ix_generation_tasks_provider_task_id", "provider_task_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    model_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("video_models.id", ondelete="RESTRICT"), nullable=False)
    generation_type: Mapped[GenerationType] = mapped_column(
        Enum(GenerationType, values_callable=lambda values: [item.value for item in values], native_enum=False),
        nullable=False,
    )
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    source_image_url: Mapped[str | None] = mapped_column(String(1000))
    source_image_storage_key: Mapped[str | None] = mapped_column(String(500))
    duration: Mapped[int | None] = mapped_column(Integer)
    aspect_ratio: Mapped[str | None] = mapped_column(String(30))
    resolution: Mapped[str | None] = mapped_column(String(30))
    provider_task_id: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[GenerationStatus] = mapped_column(
        Enum(GenerationStatus, values_callable=lambda values: [item.value for item in values], native_enum=False),
        default=GenerationStatus.PENDING,
        nullable=False,
    )
    progress: Mapped[int | None] = mapped_column(Integer)
    error_code: Mapped[str | None] = mapped_column(String(120))
    error_message: Mapped[str | None] = mapped_column(Text)
    result_video_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("videos.id", name="fk_generation_result_video", use_alter=True, ondelete="SET NULL"),
        unique=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Video(TimestampMixin, Base):
    __tablename__ = "videos"
    __table_args__ = (
        UniqueConstraint("generation_task_id", name="uq_videos_generation_task_id"),
        Index("ix_videos_owner_id", "owner_id"),
        Index("ix_videos_created_at", "created_at"),
        Index("ix_videos_is_deleted", "is_deleted"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    generation_task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("video_generation_tasks.id", ondelete="RESTRICT"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    video_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    thumbnail_url: Mapped[str | None] = mapped_column(String(1000))
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    thumbnail_storage_key: Mapped[str | None] = mapped_column(String(500))
    file_size: Mapped[int | None] = mapped_column(BigInteger)
    duration: Mapped[int | None] = mapped_column(Integer)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    mime_type: Mapped[str] = mapped_column(String(120), default="video/mp4", nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PublishPlatform(TimestampMixin, Base):
    __tablename__ = "publish_platforms"
    __table_args__ = (Index("ix_publish_platforms_enabled", "enabled"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    code: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    adapter_type: Mapped[str] = mapped_column(String(80), nullable=False)
    api_base_url: Mapped[str | None] = mapped_column(String(500))
    capabilities: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    extra_config: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class PublishAccount(TimestampMixin, Base):
    __tablename__ = "publish_accounts"
    __table_args__ = (
        Index("ix_publish_accounts_platform_id", "platform_id"),
        Index("ix_publish_accounts_enabled", "enabled"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    platform_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("publish_platforms.id", ondelete="RESTRICT"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    account_identifier: Mapped[str | None] = mapped_column(String(255))
    client_id_encrypted: Mapped[str | None] = mapped_column(Text)
    client_secret_encrypted: Mapped[str | None] = mapped_column(Text)
    access_token_encrypted: Mapped[str | None] = mapped_column(Text)
    refresh_token_encrypted: Mapped[str | None] = mapped_column(Text)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    extra_config: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class PublishTask(TimestampMixin, Base):
    __tablename__ = "publish_tasks"
    __table_args__ = (
        Index("ix_publish_tasks_video_id", "video_id"),
        Index("ix_publish_tasks_user_id", "user_id"),
        Index("ix_publish_tasks_platform_id", "platform_id"),
        Index("ix_publish_tasks_account_id", "account_id"),
        Index("ix_publish_tasks_status", "status"),
        Index("ix_publish_tasks_created_at", "created_at"),
        Index("ix_publish_tasks_idempotency_key", "idempotency_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    video_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("videos.id", ondelete="RESTRICT"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    platform_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("publish_platforms.id", ondelete="RESTRICT"), nullable=False
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("publish_accounts.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[PublishStatus] = mapped_column(
        Enum(PublishStatus, values_callable=lambda values: [item.value for item in values], native_enum=False),
        default=PublishStatus.PENDING,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    content: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[list[str]] = mapped_column(JSON_TYPE, default=list, nullable=False)
    platform_overrides: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    platform_post_id: Mapped[str | None] = mapped_column(String(255))
    platform_post_url: Mapped[str | None] = mapped_column(String(1000))
    idempotency_key: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(120))
    error_message: Mapped[str | None] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_user_id", "user_id"),
        Index("ix_audit_logs_action", "action"),
        Index("ix_audit_logs_resource_type", "resource_type"),
        Index("ix_audit_logs_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(120), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(120))
    result: Mapped[AuditResult] = mapped_column(
        Enum(AuditResult, values_callable=lambda values: [item.value for item in values], native_enum=False),
        nullable=False,
    )
    ip_address: Mapped[str | None] = mapped_column(String(64))
    message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
