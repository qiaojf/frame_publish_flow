import uuid
from typing import Any

from app.adapters.publishing.base import (
    PermanentPublishError,
    PublishPlatformAdapter,
    PublishRequest,
    PublishResult,
)


class MockPublishAdapter(PublishPlatformAdapter):
    def __init__(self, account_config: dict[str, Any] | None = None) -> None:
        self.account_config = account_config or {}

    async def publish_video(self, request: PublishRequest) -> PublishResult:
        mode = str(self.account_config.get("simulate_result", "success"))
        if mode == "failed":
            raise PermanentPublishError("Mock 账号配置为模拟发布失败")
        if mode == "processing":
            return PublishResult(status="processing", platform_post_id=f"mock-post-{uuid.uuid4().hex}")
        post_id = f"mock-post-{uuid.uuid4().hex}"
        return PublishResult(
            status="success",
            platform_post_id=post_id,
            platform_post_url=f"https://mock.local/posts/{post_id}",
        )

    async def get_publish_status(self, platform_post_id: str) -> PublishResult:
        return PublishResult(
            status="success",
            platform_post_id=platform_post_id,
            platform_post_url=f"https://mock.local/posts/{platform_post_id}",
        )

    async def refresh_token(self) -> None:
        return None
