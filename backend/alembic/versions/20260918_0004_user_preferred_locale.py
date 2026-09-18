"""Add the user's preferred interface locale.

Revision ID: 20260918_0004
Revises: 20260910_0003
Create Date: 2026-09-18
"""

from collections.abc import Sequence
import os

from alembic import op
import sqlalchemy as sa

revision: str = "20260918_0004"
down_revision: str | None = "20260910_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    configured_default = os.getenv("DEFAULT_LOCALE", "zh-CN")
    default_locale = configured_default if configured_default in {"zh-CN", "ja-JP", "en-US"} else "zh-CN"
    op.add_column(
        "users",
        sa.Column("preferred_locale", sa.String(10), server_default=default_locale, nullable=False),
    )
    op.create_check_constraint(
        "ck_users_preferred_locale",
        "users",
        "preferred_locale IN ('zh-CN', 'ja-JP', 'en-US')",
    )
    op.alter_column("users", "preferred_locale", server_default=None)


def downgrade() -> None:
    op.drop_constraint("ck_users_preferred_locale", "users", type_="check")
    op.drop_column("users", "preferred_locale")
