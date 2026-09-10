import uuid
from datetime import datetime

from pydantic import BaseModel

from app.core.enums import GenerationStatus, GenerationType
from app.models import VideoGenerationTask


class GenerationTaskOut(BaseModel):
    id: uuid.UUID
    status: GenerationStatus
    prompt: str
    model_id: uuid.UUID
    model_name: str | None = None
    generation_type: GenerationType
    error_code: str | None = None
    error_message: str | None = None
    video_id: uuid.UUID | None = None
    duration: int | None = None
    aspect_ratio: str | None = None
    resolution: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None

    @classmethod
    def from_model(cls, task: VideoGenerationTask, model_name: str | None = None) -> "GenerationTaskOut":
        return cls(
            id=task.id,
            status=task.status,
            prompt=task.prompt,
            model_id=task.model_id,
            model_name=model_name,
            generation_type=task.generation_type,
            error_code=task.error_code,
            error_message=task.error_message,
            video_id=task.result_video_id,
            duration=task.duration,
            aspect_ratio=task.aspect_ratio,
            resolution=task.resolution,
            created_at=task.created_at,
            started_at=task.started_at,
            completed_at=task.completed_at,
        )
