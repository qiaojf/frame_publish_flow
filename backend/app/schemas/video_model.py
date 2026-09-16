import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator

from app.core.security import mask_secret
from app.models import ModelAccount, ModelProvider, VideoModel


class VideoModelCapabilities(BaseModel):
    text_to_video: bool | None = None
    image_to_video: bool | None = None
    duration_mode: str | None = None
    durations: list[int] | None = None
    duration_min: int | None = None
    duration_max: int | None = None
    aspect_ratios: list[str] | None = None
    aspect_ratios_text_to_video: list[str] | None = None
    aspect_ratios_image_to_video: list[str] | None = None
    resolutions: list[str] | None = None
    resolution_duration_matrix: dict[str, list[int]] | None = None
    max_images: int | None = None
    max_image_size_mb: int | None = None

    model_config = {"extra": "allow"}


class ModelProviderOut(BaseModel):
    id: uuid.UUID
    name: str
    code: str
    adapter_family: str
    default_api_base_url: str | None = None
    default_api_version: str | None = None
    auth_type: str
    provider_capabilities: dict[str, Any]
    extra_config: dict[str, Any]
    enabled: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, provider: ModelProvider) -> "ModelProviderOut":
        return cls.model_validate(provider, from_attributes=True)


class ModelProviderCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    code: str = Field(min_length=2, max_length=80, pattern=r"^[A-Za-z0-9_.-]+$")
    adapter_family: str = Field(min_length=1, max_length=80)
    default_api_base_url: str | None = Field(default=None, max_length=500)
    default_api_version: str | None = Field(default=None, max_length=80)
    auth_type: str = Field(default="api_key", min_length=1, max_length=80)
    provider_capabilities: dict[str, Any] = Field(default_factory=dict)
    extra_config: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True


class ModelProviderUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    code: str | None = Field(default=None, min_length=2, max_length=80, pattern=r"^[A-Za-z0-9_.-]+$")
    adapter_family: str | None = Field(default=None, min_length=1, max_length=80)
    default_api_base_url: str | None = Field(default=None, max_length=500)
    default_api_version: str | None = Field(default=None, max_length=80)
    auth_type: str | None = Field(default=None, min_length=1, max_length=80)
    provider_capabilities: dict[str, Any] | None = None
    extra_config: dict[str, Any] | None = None
    enabled: bool | None = None


class ModelAccountOut(BaseModel):
    id: uuid.UUID
    provider_id: uuid.UUID
    provider_name: str | None = None
    name: str
    account_identifier: str | None = None
    api_base_url: str | None = None
    api_version: str | None = None
    api_key_masked: str | None = None
    access_token_masked: str | None = None
    project_id: str | None = None
    region: str | None = None
    service_account_ref: str | None = None
    credential_extra: dict[str, Any] | None = None
    extra_config: dict[str, Any] | None = None
    enabled: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, account: ModelAccount, *, admin: bool = True) -> "ModelAccountOut":
        return cls(
            id=account.id,
            provider_id=account.provider_id,
            provider_name=account.provider.name if account.provider else None,
            name=account.name,
            account_identifier=account.account_identifier,
            api_base_url=account.api_base_url,
            api_version=account.api_version,
            api_key_masked=mask_secret(account.api_key_encrypted) if admin else None,
            access_token_masked=mask_secret(account.access_token_encrypted) if admin else None,
            project_id=account.project_id,
            region=account.region,
            service_account_ref=account.service_account_ref,
            credential_extra={"configured": bool(account.credential_extra)} if admin else None,
            extra_config=account.extra_config if admin else None,
            enabled=account.enabled,
            created_at=account.created_at,
            updated_at=account.updated_at,
        )


class ModelAccountCreate(BaseModel):
    provider_id: uuid.UUID
    name: str = Field(min_length=1, max_length=160)
    account_identifier: str | None = Field(default=None, max_length=255)
    api_base_url: str | None = Field(default=None, max_length=500)
    api_version: str | None = Field(default=None, max_length=80)
    api_key: str | None = Field(default=None, max_length=8000)
    access_token: str | None = Field(default=None, max_length=8000)
    project_id: str | None = Field(default=None, max_length=255)
    region: str | None = Field(default=None, max_length=120)
    service_account_ref: str | None = Field(default=None, max_length=500)
    credential_extra: dict[str, Any] = Field(default_factory=dict)
    extra_config: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True


class ModelAccountUpdate(BaseModel):
    provider_id: uuid.UUID | None = None
    name: str | None = Field(default=None, min_length=1, max_length=160)
    account_identifier: str | None = Field(default=None, max_length=255)
    api_base_url: str | None = Field(default=None, max_length=500)
    api_version: str | None = Field(default=None, max_length=80)
    api_key: str | None = Field(default=None, max_length=8000)
    access_token: str | None = Field(default=None, max_length=8000)
    project_id: str | None = Field(default=None, max_length=255)
    region: str | None = Field(default=None, max_length=120)
    service_account_ref: str | None = Field(default=None, max_length=500)
    credential_extra: dict[str, Any] | None = None
    extra_config: dict[str, Any] | None = None
    enabled: bool | None = None


class VideoModelOut(BaseModel):
    id: uuid.UUID
    model_account_id: uuid.UUID
    account_name: str | None = None
    provider_id: uuid.UUID | None = None
    provider: str
    provider_code: str | None = None
    name: str
    code: str
    adapter_type: str | None = None
    description: str | None = None
    supports_text_to_video: bool
    supports_image_to_video: bool
    capabilities: dict[str, Any]
    request_defaults: dict[str, Any]
    enabled: bool
    api_base_url: str | None = None
    api_version: str | None = None
    model_id: str | None = None
    api_key_masked: str | None = None
    timeout_seconds: int | None = None
    extra_config: dict[str, Any] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def from_model(cls, model: VideoModel, *, admin: bool = False) -> "VideoModelOut":
        account = model.model_account
        provider = account.provider
        return cls(
            id=model.id,
            model_account_id=model.model_account_id,
            account_name=account.name if admin else None,
            provider_id=provider.id if admin else None,
            provider=provider.name,
            provider_code=provider.code,
            name=model.name,
            code=model.code,
            adapter_type=model.adapter_type if admin else None,
            description=model.description,
            supports_text_to_video=model.supports_text_to_video,
            supports_image_to_video=model.supports_image_to_video,
            capabilities=model.capabilities,
            request_defaults=model.request_defaults,
            enabled=model.enabled,
            api_base_url=(account.api_base_url or provider.default_api_base_url) if admin else None,
            api_version=(account.api_version or provider.default_api_version) if admin else None,
            model_id=model.model_id if admin else None,
            api_key_masked=mask_secret(account.api_key_encrypted) if admin else None,
            timeout_seconds=model.timeout_seconds if admin else None,
            extra_config=model.extra_config if admin else None,
            created_at=model.created_at if admin else None,
            updated_at=model.updated_at if admin else None,
        )


class VideoModelCreate(BaseModel):
    model_account_id: uuid.UUID | None = None
    name: str = Field(min_length=1, max_length=120)
    code: str = Field(min_length=2, max_length=80, pattern=r"^[A-Za-z0-9_.-]+$")
    model_id: str | None = Field(default=None, max_length=200)
    adapter_type: str = Field(default="mock_video", min_length=1, max_length=80)
    description: str | None = None
    supports_text_to_video: bool = False
    supports_image_to_video: bool = False
    capabilities: dict[str, Any] = Field(default_factory=dict)
    request_defaults: dict[str, Any] = Field(default_factory=dict)
    extra_config: dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: int = Field(default=300, ge=1, le=3600)
    enabled: bool = True
    # v1 compatibility: the service converts these into a dedicated provider/account.
    provider: str | None = Field(default=None, min_length=1, max_length=120)
    api_base_url: str | None = Field(default=None, max_length=500)
    api_key: str | None = Field(default=None, max_length=8000)

    @model_validator(mode="after")
    def require_account_or_legacy_provider(self) -> "VideoModelCreate":
        if self.model_account_id is None and not self.provider:
            raise ValueError("model_account_id 为必填；兼容旧请求时可提供 provider")
        return self


class VideoModelUpdate(BaseModel):
    model_account_id: uuid.UUID | None = None
    name: str | None = Field(default=None, min_length=1, max_length=120)
    code: str | None = Field(default=None, min_length=2, max_length=80, pattern=r"^[A-Za-z0-9_.-]+$")
    model_id: str | None = Field(default=None, max_length=200)
    adapter_type: str | None = Field(default=None, min_length=1, max_length=80)
    description: str | None = None
    supports_text_to_video: bool | None = None
    supports_image_to_video: bool | None = None
    capabilities: dict[str, Any] | None = None
    request_defaults: dict[str, Any] | None = None
    extra_config: dict[str, Any] | None = None
    timeout_seconds: int | None = Field(default=None, ge=1, le=3600)
    enabled: bool | None = None
    # Accepted for v1 clients; these update the linked account/provider.
    provider: str | None = Field(default=None, min_length=1, max_length=120)
    api_base_url: str | None = Field(default=None, max_length=500)
    api_key: str | None = Field(default=None, max_length=8000)


class AdapterTestResult(BaseModel):
    configured: bool
    adapter_type: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
