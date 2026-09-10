import uuid
from datetime import datetime

from pydantic import BaseModel

from app.core.enums import GenerationStatus, GenerationType
from app.models import Video, VideoGenerationTask


class VideoOut(BaseModel):
    id: uuid.UUID
    title: str
    prompt: str
    description: str | None = None
    thumbnail_url: str | None = None
    video_url: str
    reference_image_url: str | None = None
    generation_type: GenerationType
    model_id: uuid.UUID
    model_name: str
    duration: int | None = None
    resolution: str | None = None
    aspect_ratio: str | None = None
    width: int | None = None
    height: int | None = None
    file_size: int | None = None
    generation_status: GenerationStatus
    publish_status: str
    created_at: datetime

    @classmethod
    def from_models(
        cls,
        video: Video,
        task: VideoGenerationTask,
        model_name: str,
        publish_status: str = "not_published",
    ) -> "VideoOut":
        return cls(
            id=video.id,
            title=video.title,
            prompt=task.prompt,
            description=video.description,
            thumbnail_url=video.thumbnail_url,
            video_url=video.video_url,
            reference_image_url=task.source_image_url,
            generation_type=task.generation_type,
            model_id=task.model_id,
            model_name=model_name,
            duration=video.duration or task.duration,
            resolution=task.resolution,
            aspect_ratio=task.aspect_ratio,
            width=video.width,
            height=video.height,
            file_size=video.file_size,
            generation_status=task.status,
            publish_status=publish_status,
            created_at=video.created_at,
        )
