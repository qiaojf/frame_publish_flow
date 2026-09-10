import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.core.security import mask_secret
from app.models import PublishAccount, PublishPlatform


class PublishAccountOut(BaseModel):
    id: uuid.UUID
    platform_id: uuid.UUID
    name: str
    account_identifier: str | None = None
    enabled: bool
    client_id_masked: str | None = None
    client_secret_masked: str | None = None
    access_token_masked: str | None = None
    refresh_token_masked: str | None = None
    token_expires_at: datetime | None = None
    extra_config: dict[str, Any] | None = None
    created_at: datetime | None = None

    @classmethod
    def from_model(cls, account: PublishAccount, *, admin: bool = False) -> "PublishAccountOut":
        return cls(
            id=account.id,
            platform_id=account.platform_id,
            name=account.name,
            account_identifier=account.account_identifier,
            enabled=account.enabled,
            client_id_masked=mask_secret(account.client_id_encrypted) if admin else None,
            client_secret_masked=mask_secret(account.client_secret_encrypted) if admin else None,
            access_token_masked=mask_secret(account.access_token_encrypted) if admin else None,
            refresh_token_masked=mask_secret(account.refresh_token_encrypted) if admin else None,
            token_expires_at=account.token_expires_at,
            extra_config=account.extra_config if admin else None,
            created_at=account.created_at if admin else None,
        )


class PublishPlatformOut(BaseModel):
    id: uuid.UUID
    name: str
    code: str
    adapter_type: str | None = None
    api_base_url: str | None = None
    description: str | None = None
    capabilities: dict[str, Any]
    enabled: bool
    accounts: list[PublishAccountOut] | None = None
    extra_config: dict[str, Any] | None = None
    created_at: datetime | None = None

    @classmethod
    def from_model(
        cls,
        platform: PublishPlatform,
        *,
        accounts: list[PublishAccount] | None = None,
        admin: bool = False,
    ) -> "PublishPlatformOut":
        return cls(
            id=platform.id,
            name=platform.name,
            code=platform.code,
            adapter_type=platform.adapter_type if admin else None,
            api_base_url=platform.api_base_url if admin else None,
            description=platform.description,
            capabilities=platform.capabilities,
            enabled=platform.enabled,
            accounts=[PublishAccountOut.from_model(account, admin=False) for account in accounts or []]
            if accounts is not None
            else None,
            extra_config=platform.extra_config if admin else None,
            created_at=platform.created_at if admin else None,
        )


class PublishPlatformCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    code: str = Field(min_length=2, max_length=80, pattern=r"^[A-Za-z0-9_.-]+$")
    adapter_type: str = Field(min_length=1, max_length=80)
    api_base_url: str | None = Field(default=None, max_length=500)
    description: str | None = None
    capabilities: dict[str, Any] = Field(default_factory=dict)
    extra_config: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True


class PublishPlatformUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    code: str | None = Field(default=None, min_length=2, max_length=80, pattern=r"^[A-Za-z0-9_.-]+$")
    adapter_type: str | None = Field(default=None, min_length=1, max_length=80)
    api_base_url: str | None = Field(default=None, max_length=500)
    description: str | None = None
    capabilities: dict[str, Any] | None = None
    extra_config: dict[str, Any] | None = None
    enabled: bool | None = None


class PublishAccountCreate(BaseModel):
    platform_id: uuid.UUID
    name: str = Field(min_length=1, max_length=160)
    account_identifier: str | None = Field(default=None, max_length=255)
    client_id: str | None = None
    client_secret: str | None = None
    access_token: str | None = None
    refresh_token: str | None = None
    token_expires_at: datetime | None = None
    extra_config: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True


class PublishAccountUpdate(BaseModel):
    platform_id: uuid.UUID | None = None
    name: str | None = Field(default=None, min_length=1, max_length=160)
    account_identifier: str | None = Field(default=None, max_length=255)
    client_id: str | None = None
    client_secret: str | None = None
    access_token: str | None = None
    refresh_token: str | None = None
    token_expires_at: datetime | None = None
    extra_config: dict[str, Any] | None = None
    enabled: bool | None = None
