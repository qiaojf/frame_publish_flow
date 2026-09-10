from collections.abc import Callable

from app.adapters.publishing.base import (
    PermanentPublishError,
    PublishPlatformAdapter,
    PublishRequest,
    PublishResult,
)
from app.adapters.publishing.mock import MockPublishAdapter
from app.models import PublishAccount, PublishPlatform


class UnconfiguredPublishAdapter(MockPublishAdapter):
    def __init__(self, platform_name: str) -> None:
        self.platform_name = platform_name

    async def publish_video(self, request: PublishRequest) -> PublishResult:
        raise PermanentPublishError(f"{self.platform_name} 真实适配器尚未配置，未执行外部发布")


class PublishAdapterFactory:
    _registry: dict[str, Callable[[PublishPlatform, PublishAccount], PublishPlatformAdapter]] = {
        "mock_publish": lambda platform, account: MockPublishAdapter(account.extra_config),
        "youtube": lambda platform, account: UnconfiguredPublishAdapter(platform.name),
        "x": lambda platform, account: UnconfiguredPublishAdapter(platform.name),
        "instagram": lambda platform, account: UnconfiguredPublishAdapter(platform.name),
        "whatsapp": lambda platform, account: UnconfiguredPublishAdapter(platform.name),
    }

    @classmethod
    def register(
        cls,
        adapter_type: str,
        builder: Callable[[PublishPlatform, PublishAccount], PublishPlatformAdapter],
    ) -> None:
        cls._registry[adapter_type] = builder

    @classmethod
    def create(cls, platform: PublishPlatform, account: PublishAccount) -> PublishPlatformAdapter:
        builder = cls._registry.get(platform.adapter_type)
        if builder is None:
            raise RuntimeError(f"发布适配器“{platform.adapter_type}”尚未实现或注册")
        return builder(platform, account)
