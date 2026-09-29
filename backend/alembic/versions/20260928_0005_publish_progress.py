"""Persist publishing upload progress.

Revision ID: 20260928_0005
Revises: 20260918_0004
Create Date: 2026-09-28
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260928_0005"
down_revision: str | None = "20260918_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "publish_tasks",
        sa.Column("progress", sa.Integer(), server_default="0", nullable=False),
    )
    op.alter_column("publish_tasks", "progress", server_default=None)


def downgrade() -> None:
    op.drop_column("publish_tasks", "progress")
