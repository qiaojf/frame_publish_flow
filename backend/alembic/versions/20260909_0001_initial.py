"""Initial FrameFlow schema.

Revision ID: 20260909_0001
Revises:
Create Date: 2026-09-09
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260909_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

user_role = sa.Enum("admin", "user", name="user_role", native_enum=False)
generation_type = sa.Enum("text_to_video", "image_to_video", name="generation_type", native_enum=False)
generation_status = sa.Enum(
    "pending", "processing", "success", "failed", "cancelled", "timeout",
    name="generation_status", native_enum=False,
)
publish_status = sa.Enum(
    "pending", "publishing", "success", "failed", "cancelled",
    name="publish_status", native_enum=False,
)
audit_result = sa.Enum("success", "failed", name="audit_result", native_enum=False)


def timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("username", sa.String(80), nullable=False),
        sa.Column("display_name", sa.String(120)),
        sa.Column("email", sa.String(255)),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True)),
        *timestamps(),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("username", name="uq_users_username"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_username", "users", ["username"])
    op.create_index("ix_users_role", "users", ["role"])
    op.create_index("ix_users_enabled", "users", ["enabled"])

    op.create_table(
        "video_models",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("code", sa.String(80), nullable=False),
        sa.Column("provider", sa.String(80), nullable=False),
        sa.Column("adapter_type", sa.String(80), nullable=False),
        sa.Column("api_base_url", sa.String(500)),
        sa.Column("api_key_encrypted", sa.Text()),
        sa.Column("model_id", sa.String(200)),
        sa.Column("supports_text_to_video", sa.Boolean(), nullable=False),
        sa.Column("supports_image_to_video", sa.Boolean(), nullable=False),
        sa.Column("capabilities", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("extra_config", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        *timestamps(),
        sa.PrimaryKeyConstraint("id", name="pk_video_models"),
        sa.UniqueConstraint("code", name="uq_video_models_code"),
    )
    op.create_index("ix_video_models_enabled", "video_models", ["enabled"])

    op.create_table(
        "video_generation_tasks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("model_id", sa.Uuid(), nullable=False),
        sa.Column("generation_type", generation_type, nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("source_image_url", sa.String(1000)),
        sa.Column("source_image_storage_key", sa.String(500)),
        sa.Column("duration", sa.Integer()),
        sa.Column("aspect_ratio", sa.String(30)),
        sa.Column("resolution", sa.String(30)),
        sa.Column("provider_task_id", sa.String(255)),
        sa.Column("status", generation_status, nullable=False),
        sa.Column("progress", sa.Integer()),
        sa.Column("error_code", sa.String(120)),
        sa.Column("error_message", sa.Text()),
        sa.Column("result_video_id", sa.Uuid()),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        *timestamps(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT", name="fk_generation_user"),
        sa.ForeignKeyConstraint(["model_id"], ["video_models.id"], ondelete="RESTRICT", name="fk_generation_model"),
        sa.PrimaryKeyConstraint("id", name="pk_video_generation_tasks"),
        sa.UniqueConstraint("result_video_id", name="uq_generation_result_video"),
    )
    op.create_index("ix_generation_tasks_user_id", "video_generation_tasks", ["user_id"])
    op.create_index("ix_generation_tasks_model_id", "video_generation_tasks", ["model_id"])
    op.create_index("ix_generation_tasks_status", "video_generation_tasks", ["status"])
    op.create_index("ix_generation_tasks_created_at", "video_generation_tasks", ["created_at"])
    op.create_index("ix_generation_tasks_provider_task_id", "video_generation_tasks", ["provider_task_id"])

    op.create_table(
        "videos",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("generation_task_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(240), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("video_url", sa.String(1000), nullable=False),
        sa.Column("thumbnail_url", sa.String(1000)),
        sa.Column("storage_key", sa.String(500), nullable=False),
        sa.Column("thumbnail_storage_key", sa.String(500)),
        sa.Column("file_size", sa.BigInteger()),
        sa.Column("duration", sa.Integer()),
        sa.Column("width", sa.Integer()),
        sa.Column("height", sa.Integer()),
        sa.Column("mime_type", sa.String(120), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        *timestamps(),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="RESTRICT", name="fk_videos_owner"),
        sa.ForeignKeyConstraint(["generation_task_id"], ["video_generation_tasks.id"], ondelete="RESTRICT", name="fk_videos_generation_task"),
        sa.PrimaryKeyConstraint("id", name="pk_videos"),
        sa.UniqueConstraint("generation_task_id", name="uq_videos_generation_task_id"),
    )
    op.create_index("ix_videos_owner_id", "videos", ["owner_id"])
    op.create_index("ix_videos_created_at", "videos", ["created_at"])
    op.create_index("ix_videos_is_deleted", "videos", ["is_deleted"])
    op.create_foreign_key(
        "fk_generation_result_video", "video_generation_tasks", "videos",
        ["result_video_id"], ["id"], ondelete="SET NULL",
    )

    op.create_table(
        "publish_platforms",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("code", sa.String(80), nullable=False),
        sa.Column("adapter_type", sa.String(80), nullable=False),
        sa.Column("api_base_url", sa.String(500)),
        sa.Column("capabilities", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("extra_config", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        *timestamps(),
        sa.PrimaryKeyConstraint("id", name="pk_publish_platforms"),
        sa.UniqueConstraint("code", name="uq_publish_platforms_code"),
    )
    op.create_index("ix_publish_platforms_enabled", "publish_platforms", ["enabled"])

    op.create_table(
        "publish_accounts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("platform_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("account_identifier", sa.String(255)),
        sa.Column("client_id_encrypted", sa.Text()),
        sa.Column("client_secret_encrypted", sa.Text()),
        sa.Column("access_token_encrypted", sa.Text()),
        sa.Column("refresh_token_encrypted", sa.Text()),
        sa.Column("token_expires_at", sa.DateTime(timezone=True)),
        sa.Column("extra_config", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(["platform_id"], ["publish_platforms.id"], ondelete="RESTRICT", name="fk_publish_accounts_platform"),
        sa.PrimaryKeyConstraint("id", name="pk_publish_accounts"),
    )
    op.create_index("ix_publish_accounts_platform_id", "publish_accounts", ["platform_id"])
    op.create_index("ix_publish_accounts_enabled", "publish_accounts", ["enabled"])

    op.create_table(
        "publish_tasks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("video_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("platform_id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("status", publish_status, nullable=False),
        sa.Column("title", sa.String(240), nullable=False),
        sa.Column("content", sa.Text()),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("platform_overrides", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("platform_post_id", sa.String(255)),
        sa.Column("platform_post_url", sa.String(1000)),
        sa.Column("idempotency_key", sa.String(160), nullable=False),
        sa.Column("error_code", sa.String(120)),
        sa.Column("error_message", sa.Text()),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        *timestamps(),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="RESTRICT", name="fk_publish_tasks_video"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT", name="fk_publish_tasks_user"),
        sa.ForeignKeyConstraint(["platform_id"], ["publish_platforms.id"], ondelete="RESTRICT", name="fk_publish_tasks_platform"),
        sa.ForeignKeyConstraint(["account_id"], ["publish_accounts.id"], ondelete="RESTRICT", name="fk_publish_tasks_account"),
        sa.PrimaryKeyConstraint("id", name="pk_publish_tasks"),
        sa.UniqueConstraint("idempotency_key", name="uq_publish_tasks_idempotency_key"),
    )
    op.create_index("ix_publish_tasks_video_id", "publish_tasks", ["video_id"])
    op.create_index("ix_publish_tasks_user_id", "publish_tasks", ["user_id"])
    op.create_index("ix_publish_tasks_platform_id", "publish_tasks", ["platform_id"])
    op.create_index("ix_publish_tasks_account_id", "publish_tasks", ["account_id"])
    op.create_index("ix_publish_tasks_status", "publish_tasks", ["status"])
    op.create_index("ix_publish_tasks_created_at", "publish_tasks", ["created_at"])
    op.create_index("ix_publish_tasks_idempotency_key", "publish_tasks", ["idempotency_key"])

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid()),
        sa.Column("action", sa.String(120), nullable=False),
        sa.Column("resource_type", sa.String(120), nullable=False),
        sa.Column("resource_id", sa.String(120)),
        sa.Column("result", audit_result, nullable=False),
        sa.Column("ip_address", sa.String(64)),
        sa.Column("message", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL", name="fk_audit_logs_user"),
        sa.PrimaryKeyConstraint("id", name="pk_audit_logs"),
    )
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_resource_type", "audit_logs", ["resource_type"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("publish_tasks")
    op.drop_table("publish_accounts")
    op.drop_table("publish_platforms")
    op.drop_constraint("fk_generation_result_video", "video_generation_tasks", type_="foreignkey")
    op.drop_table("videos")
    op.drop_table("video_generation_tasks")
    op.drop_table("video_models")
    op.drop_table("users")
