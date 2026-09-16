import uuid
from datetime import datetime
from typing import Any

from pydantic import AliasChoices, BaseModel, Field, model_validator

from app.core.enums import PublishStatus
from app.models import PublishTask


class PublishTarget(BaseModel):
    platform_id: uuid.UUID
    account_id: uuid.UUID
    publish_type: str = Field(default="video", pattern=r"^(video|reel|post)$")
    overrides: dict[str, Any] = Field(default_factory=dict)


class PublishCommon(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    content: str | None = None
    description: str | None = None
    tags: list[str] = Field(default_factory=list, max_length=100)


class PublishBatchCreate(BaseModel):
    video_id: uuid.UUID
    common: PublishCommon | None = None
    title: str | None = Field(default=None, min_length=1, max_length=240)
    content: str | None = None
    description: str | None = Field(
        default=None,
        validation_alias=AliasChoices("description", "content"),
    )
    tags: list[str] = Field(default_factory=list, max_length=100)
    targets: list[PublishTarget] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def normalize_common(self) -> "PublishBatchCreate":
        if self.common:
            self.title = self.common.title
            self.content = self.common.content
            self.description = self.common.description or self.common.content
            self.tags = self.common.tags
        elif not self.title:
            raise ValueError("title 或 common.title 为必填")
        elif self.content is None:
            self.content = self.description
        return self

    def common_payload(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "content": self.content,
            "description": self.description,
            "tags": self.tags,
        }


class PublishTaskOut(BaseModel):
    id: uuid.UUID
    video_id: uuid.UUID
    video_title: str | None = None
    video_thumbnail_url: str | None = None
    video_url: str | None = None
    platform_id: uuid.UUID
    platform_name: str
    account_id: uuid.UUID
    account_name: str
    publish_type: str
    status: PublishStatus
    published_at: datetime | None = None
    created_at: datetime
    publish_url: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    retry_count: int
    provider_upload_id: str | None = None
    provider_container_id: str | None = None
    platform_post_id: str | None = None

    @classmethod
    def from_model(
        cls,
        task: PublishTask,
        *,
        video_title: str | None = None,
        video_thumbnail_url: str | None = None,
        video_url: str | None = None,
        platform_name: str,
        account_name: str,
    ) -> "PublishTaskOut":
        publish_url = task.platform_post_url
        if task.platform_post_id and (
            not publish_url
            or publish_url.startswith("https://mock.local/posts/")
            or publish_url.startswith("http://mock.local/posts/")
        ):
            publish_url = f"/publish/{task.platform_post_id}"
        return cls(
            id=task.id,
            video_id=task.video_id,
            video_title=video_title,
            video_thumbnail_url=video_thumbnail_url,
            video_url=video_url,
            platform_id=task.platform_id,
            platform_name=platform_name,
            account_id=task.account_id,
            account_name=account_name,
            publish_type=task.publish_type,
            status=task.status,
            published_at=task.completed_at,
            created_at=task.created_at,
            publish_url=publish_url,
            error_code=task.error_code,
            error_message=task.error_message,
            retry_count=task.retry_count,
            provider_upload_id=task.provider_upload_id,
            provider_container_id=task.provider_container_id,
            platform_post_id=task.platform_post_id,
        )


class PublishBatchOut(BaseModel):
    tasks: list[PublishTaskOut]
