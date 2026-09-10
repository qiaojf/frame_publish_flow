import uuid
from datetime import datetime
from typing import Any

from pydantic import AliasChoices, BaseModel, Field

from app.models import PublishTask


class PublishTarget(BaseModel):
    platform_id: uuid.UUID
    account_id: uuid.UUID
    overrides: dict[str, Any] = Field(default_factory=dict)


class PublishBatchCreate(BaseModel):
    video_id: uuid.UUID
    title: str = Field(min_length=1, max_length=240)
    description: str | None = Field(
        default=None,
        validation_alias=AliasChoices("description", "content"),
    )
    tags: list[str] = Field(default_factory=list, max_length=100)
    targets: list[PublishTarget] = Field(min_length=1, max_length=20)


class PublishTaskOut(BaseModel):
    id: uuid.UUID
    video_id: uuid.UUID
    video_title: str | None = None
    video_thumbnail_url: str | None = None
    platform_id: uuid.UUID
    platform_name: str
    account_id: uuid.UUID
    account_name: str
    status: str
    published_at: datetime | None = None
    created_at: datetime
    publish_url: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    retry_count: int

    @classmethod
    def from_model(
        cls,
        task: PublishTask,
        *,
        video_title: str | None = None,
        video_thumbnail_url: str | None = None,
        platform_name: str,
        account_name: str,
    ) -> "PublishTaskOut":
        return cls(
            id=task.id,
            video_id=task.video_id,
            video_title=video_title,
            video_thumbnail_url=video_thumbnail_url,
            platform_id=task.platform_id,
            platform_name=platform_name,
            account_id=task.account_id,
            account_name=account_name,
            status=task.status.value,
            published_at=task.completed_at,
            created_at=task.created_at,
            publish_url=task.platform_post_url,
            error_code=task.error_code,
            error_message=task.error_message,
            retry_count=task.retry_count,
        )


class PublishBatchOut(BaseModel):
    tasks: list[PublishTaskOut]
