import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class GenerationRequest:
    prompt: str
    duration: int | None
    aspect_ratio: str | None
    resolution: str | None
    source_image_path: Path | None = None
    source_image_url: str | None = None


@dataclass(slots=True)
class GeneratedVideo:
    local_path: Path
    provider_task_id: str


class VideoModelAdapterError(RuntimeError):
    """A safe, provider-neutral error that may be persisted and returned to clients."""

    def __init__(self, error_code: str, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.safe_message = message
        self.retryable = retryable


class VideoModelAdapter(ABC):
    deferred_polling = False
    task_failure_error_code = "GENERATION_FAILED"
    task_failure_message = "视频生成失败"
    timeout_error_code = "GENERATION_TIMEOUT"
    timeout_message = "视频生成超时"

    def configuration_status(self) -> tuple[bool, str, dict[str, Any]]:
        return True, "Adapter 已加载", {}

    @property
    def poll_interval_seconds(self) -> int:
        return 2

    @property
    def generation_timeout_seconds(self) -> int | None:
        return None

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
