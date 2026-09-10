import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class GenerationRequest:
    prompt: str
    duration: int | None
    aspect_ratio: str | None
    resolution: str | None
    source_image_path: Path | None = None


@dataclass(slots=True)
class GeneratedVideo:
    local_path: Path
    provider_task_id: str


class VideoModelAdapter(ABC):
    @abstractmethod
    async def create_text_to_video(self, request: GenerationRequest) -> str:
        raise NotImplementedError

    @abstractmethod
    async def create_image_to_video(self, request: GenerationRequest) -> str:
        raise NotImplementedError

    @abstractmethod
    async def get_task_status(self, provider_task_id: str) -> str:
        raise NotImplementedError

    @abstractmethod
    async def get_result(self, provider_task_id: str, work_dir: Path) -> GeneratedVideo:
        raise NotImplementedError

    @staticmethod
    def new_provider_task_id() -> str:
        return f"mock-gen-{uuid.uuid4().hex}"
