from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Callable
from typing import Any


class TemporaryPublishError(RuntimeError):
    pass


class PermanentPublishError(RuntimeError):
    pass


@dataclass(slots=True)
class PublishRequest:
    video_path: Path
    title: str
    content: str | None
    description: str | None
    tags: list[str]
    publish_type: str
    common_payload: dict[str, Any]
    platform_payload: dict[str, Any]
    overrides: dict[str, Any]
    idempotency_key: str
    progress_callback: Callable[[int], None] | None = None
    existing_platform_post_id: str | None = None


@dataclass(slots=True)
class PublishResult:
    status: str
    platform_post_id: str | None = None
    platform_post_url: str | None = None
    provider_container_id: str | None = None
    metadata: dict[str, Any] | None = None
    publish_url: str | None = None
    platform_url: str | None = None

    def __post_init__(self) -> None:
        """Keep the former platform_post_url name compatible with canonical publish_url."""
        if self.publish_url is None:
            self.publish_url = self.platform_post_url
        elif self.platform_post_url is None:
            self.platform_post_url = self.publish_url


class PublishPlatformAdapter(ABC):
    def configuration_status(self) -> tuple[bool, str, dict[str, Any]]:
        return True, "Adapter 已加载", {}

    @abstractmethod
    async def publish_video(self, request: PublishRequest) -> PublishResult:
        raise NotImplementedError

    @abstractmethod
    async def get_publish_status(self, platform_post_id: str) -> PublishResult:
        raise NotImplementedError

    @abstractmethod
    async def refresh_token(self) -> None:
        raise NotImplementedError
