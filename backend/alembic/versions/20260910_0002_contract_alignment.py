"""Align database constraint names with ORM metadata.

Revision ID: 20260910_0002
Revises: 20260909_0001
Create Date: 2026-09-10
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260910_0002"
down_revision: str | None = "20260909_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


CONSTRAINT_RENAMES = (
    ("video_generation_tasks", "fk_generation_user", "fk_video_generation_tasks_user_id_users"),
    ("video_generation_tasks", "fk_generation_model", "fk_video_generation_tasks_model_id_video_models"),
    ("video_generation_tasks", "uq_generation_result_video", "uq_video_generation_tasks_result_video_id"),
    ("videos", "fk_videos_owner", "fk_videos_owner_id_users"),
    ("videos", "fk_videos_generation_task", "fk_videos_generation_task_id_video_generation_tasks"),
    ("publish_accounts", "fk_publish_accounts_platform", "fk_publish_accounts_platform_id_publish_platforms"),
    ("publish_tasks", "fk_publish_tasks_video", "fk_publish_tasks_video_id_videos"),
    ("publish_tasks", "fk_publish_tasks_user", "fk_publish_tasks_user_id_users"),
    ("publish_tasks", "fk_publish_tasks_platform", "fk_publish_tasks_platform_id_publish_platforms"),
    ("publish_tasks", "fk_publish_tasks_account", "fk_publish_tasks_account_id_publish_accounts"),
    ("audit_logs", "fk_audit_logs_user", "fk_audit_logs_user_id_users"),
)


def _rename_constraint(table: str, old_name: str, new_name: str) -> None:
    op.execute(
        sa.text(
            f'ALTER TABLE "{table}" RENAME CONSTRAINT "{old_name}" TO "{new_name}"'
        )
    )


def upgrade() -> None:
    op.drop_constraint("uq_users_username", "users", type_="unique")
    op.drop_index("ix_users_username", table_name="users")
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    for table, old_name, new_name in CONSTRAINT_RENAMES:
        _rename_constraint(table, old_name, new_name)


def downgrade() -> None:
    for table, old_name, new_name in reversed(CONSTRAINT_RENAMES):
        _rename_constraint(table, new_name, old_name)
    op.drop_index("ix_users_username", table_name="users")
    op.create_index("ix_users_username", "users", ["username"], unique=False)
    op.create_unique_constraint("uq_users_username", "users", ["username"])
