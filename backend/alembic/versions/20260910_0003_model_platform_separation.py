"""Separate model providers/accounts and enrich publish platform configuration.

Revision ID: 20260910_0003
Revises: 20260910_0002
Create Date: 2026-09-10
"""

from collections.abc import Sequence
import re
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260910_0003"
down_revision: str | None = "20260910_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _code(value: str, used: set[str]) -> str:
    base = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_") or "provider"
    candidate = base[:72]
    suffix = 2
    while candidate in used:
        candidate = f"{base[:68]}_{suffix}"
        suffix += 1
    used.add(candidate)
    return candidate


def upgrade() -> None:
    jsonb = postgresql.JSONB(astext_type=sa.Text())
    op.create_table(
        "model_providers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("code", sa.String(80), nullable=False),
        sa.Column("adapter_family", sa.String(80), nullable=False),
        sa.Column("default_api_base_url", sa.String(500)),
        sa.Column("default_api_version", sa.String(80)),
        sa.Column("auth_type", sa.String(80), nullable=False),
        sa.Column("provider_capabilities", jsonb, nullable=False),
        sa.Column("extra_config", jsonb, nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_model_providers"),
        sa.UniqueConstraint("code", name="uq_model_providers_code"),
    )
    op.create_index("ix_model_providers_enabled", "model_providers", ["enabled"])
    op.create_index("ix_model_providers_adapter_family", "model_providers", ["adapter_family"])

    op.create_table(
        "model_accounts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("provider_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("account_identifier", sa.String(255)),
        sa.Column("api_base_url", sa.String(500)),
        sa.Column("api_version", sa.String(80)),
        sa.Column("api_key_encrypted", sa.Text()),
        sa.Column("access_token_encrypted", sa.Text()),
        sa.Column("project_id", sa.String(255)),
        sa.Column("region", sa.String(120)),
        sa.Column("service_account_ref", sa.String(500)),
        sa.Column("credential_extra", jsonb, nullable=False),
        sa.Column("extra_config", jsonb, nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["provider_id"], ["model_providers.id"],
            name="fk_model_accounts_provider_id_model_providers", ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_model_accounts"),
    )
    op.create_index("ix_model_accounts_provider_id", "model_accounts", ["provider_id"])
    op.create_index("ix_model_accounts_enabled", "model_accounts", ["enabled"])

    op.add_column("video_models", sa.Column("model_account_id", sa.Uuid(), nullable=True))
    op.add_column(
        "video_models",
        sa.Column("request_defaults", jsonb, server_default=sa.text("'{}'::jsonb"), nullable=False),
    )

    connection = op.get_bind()
    rows = connection.execute(
        sa.text(
            "SELECT id, name, code, provider, api_base_url, api_key_encrypted, enabled "
            "FROM video_models ORDER BY created_at, id"
        )
    ).mappings().all()
    providers: dict[str, uuid.UUID] = {}
    used_codes: set[str] = set()
    for row in rows:
        provider_name = row["provider"] or "Migrated Provider"
        provider_key = provider_name.casefold()
        provider_id = providers.get(provider_key)
        if provider_id is None:
            provider_id = uuid.uuid4()
            providers[provider_key] = provider_id
            provider_code = _code(provider_name, used_codes)
            connection.execute(
                sa.text(
                    "INSERT INTO model_providers "
                    "(id, name, code, adapter_family, default_api_base_url, auth_type, "
                    "provider_capabilities, extra_config, enabled) "
                    "VALUES (:id, :name, :code, :family, :base_url, 'api_key', "
                    "CAST('{}' AS jsonb), CAST('{}' AS jsonb), true)"
                ),
                {
                    "id": provider_id,
                    "name": provider_name,
                    "code": provider_code,
                    "family": provider_code,
                    "base_url": row["api_base_url"],
                },
            )
        account_id = uuid.uuid4()
        connection.execute(
            sa.text(
                "INSERT INTO model_accounts "
                "(id, provider_id, name, account_identifier, api_base_url, api_key_encrypted, "
                "credential_extra, extra_config, enabled) "
                "VALUES (:id, :provider_id, :name, :identifier, :base_url, :api_key, "
                "CAST('{}' AS jsonb), CAST('{}' AS jsonb), :enabled)"
            ),
            {
                "id": account_id,
                "provider_id": provider_id,
                "name": f'{row["name"]} Account',
                "identifier": row["code"],
                "base_url": row["api_base_url"],
                "api_key": row["api_key_encrypted"],
                "enabled": row["enabled"],
            },
        )
        connection.execute(
            sa.text("UPDATE video_models SET model_account_id = :account_id WHERE id = :model_id"),
            {"account_id": account_id, "model_id": row["id"]},
        )

    op.alter_column("video_models", "model_account_id", nullable=False)
    op.create_foreign_key(
        "fk_video_models_model_account_id_model_accounts",
        "video_models", "model_accounts", ["model_account_id"], ["id"], ondelete="RESTRICT",
    )
    op.create_index("ix_video_models_model_account_id", "video_models", ["model_account_id"])
    op.drop_column("video_models", "api_key_encrypted")
    op.drop_column("video_models", "api_base_url")
    op.drop_column("video_models", "provider")
    op.alter_column("video_models", "request_defaults", server_default=None)

    op.add_column("publish_platforms", sa.Column("api_version", sa.String(80)))
    op.add_column(
        "publish_platforms",
        sa.Column("auth_type", sa.String(80), server_default="oauth2", nullable=False),
    )
    op.alter_column("publish_platforms", "auth_type", server_default=None)

    for name in ("external_account_id", "page_id", "channel_id", "ig_user_id"):
        op.add_column("publish_accounts", sa.Column(name, sa.String(255)))
    op.add_column(
        "publish_accounts",
        sa.Column("authorized_scopes", jsonb, server_default=sa.text("'[]'::jsonb"), nullable=False),
    )
    op.alter_column("publish_accounts", "authorized_scopes", server_default=None)

    op.add_column(
        "publish_tasks",
        sa.Column("publish_type", sa.String(40), server_default="video", nullable=False),
    )
    op.add_column("publish_tasks", sa.Column("description", sa.Text()))
    op.add_column(
        "publish_tasks",
        sa.Column("common_payload", jsonb, server_default=sa.text("'{}'::jsonb"), nullable=False),
    )
    op.add_column(
        "publish_tasks",
        sa.Column("platform_payload", jsonb, server_default=sa.text("'{}'::jsonb"), nullable=False),
    )
    op.add_column("publish_tasks", sa.Column("provider_upload_id", sa.String(255)))
    op.add_column("publish_tasks", sa.Column("provider_container_id", sa.String(255)))
    op.execute(
        "UPDATE publish_tasks SET description = content, "
        "common_payload = jsonb_build_object('title', title, 'content', content, "
        "'description', content, 'tags', tags), platform_payload = platform_overrides"
    )
    op.alter_column("publish_tasks", "publish_type", server_default=None)
    op.alter_column("publish_tasks", "common_payload", server_default=None)
    op.alter_column("publish_tasks", "platform_payload", server_default=None)


def downgrade() -> None:
    op.add_column("video_models", sa.Column("provider", sa.String(80), nullable=True))
    op.add_column("video_models", sa.Column("api_base_url", sa.String(500)))
    op.add_column("video_models", sa.Column("api_key_encrypted", sa.Text()))
    op.execute(
        "UPDATE video_models vm SET provider = mp.name, "
        "api_base_url = COALESCE(ma.api_base_url, mp.default_api_base_url), "
        "api_key_encrypted = ma.api_key_encrypted "
        "FROM model_accounts ma JOIN model_providers mp ON mp.id = ma.provider_id "
        "WHERE vm.model_account_id = ma.id"
    )
    op.alter_column("video_models", "provider", nullable=False)
    op.drop_index("ix_video_models_model_account_id", table_name="video_models")
    op.drop_constraint(
        "fk_video_models_model_account_id_model_accounts", "video_models", type_="foreignkey"
    )
    op.drop_column("video_models", "request_defaults")
    op.drop_column("video_models", "model_account_id")
    op.drop_table("model_accounts")
    op.drop_table("model_providers")

    for name in (
        "provider_container_id", "provider_upload_id", "platform_payload",
        "common_payload", "description", "publish_type",
    ):
        op.drop_column("publish_tasks", name)
    op.drop_column("publish_accounts", "authorized_scopes")
    for name in ("ig_user_id", "channel_id", "page_id", "external_account_id"):
        op.drop_column("publish_accounts", name)
    op.drop_column("publish_platforms", "auth_type")
    op.drop_column("publish_platforms", "api_version")
