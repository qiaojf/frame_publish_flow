from collections.abc import Callable

from app.adapters.publishing.base import PublishPlatformAdapter
from app.adapters.publishing.facebook import FacebookPublishAdapter
from app.adapters.publishing.instagram import InstagramPublishAdapter
from app.adapters.publishing.mock import MockPublishAdapter
from app.adapters.publishing.x import XPublishAdapter
from app.adapters.publishing.youtube import YouTubePublishAdapter
from app.models import PublishAccount, PublishPlatform


class PublishAdapterFactory:
    _registry: dict[str, Callable[[PublishPlatform, PublishAccount], PublishPlatformAdapter]] = {
        "mock_publish": lambda platform, account: MockPublishAdapter(account.extra_config),
        "x_v2": XPublishAdapter,
        "instagram_graph": InstagramPublishAdapter,
        "youtube_data_api_v3": YouTubePublishAdapter,
        "facebook_graph": FacebookPublishAdapter,
        # Compatibility with v1 configuration values.
        "x": XPublishAdapter,
        "instagram": InstagramPublishAdapter,
        "youtube": YouTubePublishAdapter,
        "facebook": FacebookPublishAdapter,
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
