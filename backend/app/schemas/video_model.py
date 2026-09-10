import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.core.security import mask_secret
from app.models import VideoModel


class VideoModelCapabilities(BaseModel):
    durations: list[int] | None = None
    aspect_ratios: list[str] | None = None
    resolutions: list[str] | None = None
    max_images: int | None = None
    max_image_size_mb: int | None = None

    model_config = ConfigDict(extra="allow")


class VideoModelOut(BaseModel):
    id: uuid.UUID
    name: str
    code: str
    provider: str
    adapter_type: str | None = None
    description: str | None = None
    supports_text_to_video: bool
    supports_image_to_video: bool
    capabilities: dict[str, Any]
    enabled: bool
    api_base_url: str | None = None
    model_id: str | None = None
    api_key_masked: str | None = None
    timeout_seconds: int | None = None
    extra_config: dict[str, Any] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def from_model(cls, model: VideoModel, *, admin: bool = False) -> "VideoModelOut":
        return cls(
            id=model.id,
            name=model.name,
            code=model.code,
            provider=model.provider,
            adapter_type=model.adapter_type if admin else None,
            description=model.description,
            supports_text_to_video=model.supports_text_to_video,
            supports_image_to_video=model.supports_image_to_video,
            capabilities=model.capabilities,
            enabled=model.enabled,
            api_base_url=model.api_base_url if admin else None,
            model_id=model.model_id if admin else None,
            api_key_masked=mask_secret(model.api_key_encrypted) if admin else None,
            timeout_seconds=model.timeout_seconds if admin else None,
            extra_config=model.extra_config if admin else None,
            created_at=model.created_at if admin else None,
            updated_at=model.updated_at if admin else None,
        )


class VideoModelCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    code: str = Field(min_length=2, max_length=80, pattern=r"^[A-Za-z0-9_.-]+$")
    provider: str = Field(min_length=1, max_length=80)
    adapter_type: str = Field(default="mock_video", min_length=1, max_length=80)
    description: str | None = None
    api_base_url: str | None = Field(default=None, max_length=500)
    api_key: str | None = Field(default=None, max_length=4000)
    model_id: str | None = Field(default=None, max_length=200)
    supports_text_to_video: bool = False
    supports_image_to_video: bool = False
    capabilities: dict[str, Any] = Field(default_factory=dict)
    extra_config: dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: int = Field(default=300, ge=1, le=3600)
    enabled: bool = True


class VideoModelUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    code: str | None = Field(default=None, min_length=2, max_length=80, pattern=r"^[A-Za-z0-9_.-]+$")
    provider: str | None = Field(default=None, min_length=1, max_length=80)
    adapter_type: str | None = Field(default=None, min_length=1, max_length=80)
    description: str | None = None
    api_base_url: str | None = Field(default=None, max_length=500)
    api_key: str | None = Field(default=None, max_length=4000)
    model_id: str | None = Field(default=None, max_length=200)
    supports_text_to_video: bool | None = None
    supports_image_to_video: bool | None = None
    capabilities: dict[str, Any] | None = None
    extra_config: dict[str, Any] | None = None
    timeout_seconds: int | None = Field(default=None, ge=1, le=3600)
    enabled: bool | None = None
