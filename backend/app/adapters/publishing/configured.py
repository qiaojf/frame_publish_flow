from datetime import UTC, datetime
from typing import Any

from app.adapters.publishing.base import (
    PermanentPublishError,
    PublishPlatformAdapter,
    PublishRequest,
    PublishResult,
    TemporaryPublishError,
)
from app.core.security import decrypt_secret
from app.models import PublishAccount, PublishPlatform


class ConfiguredPublishAdapter(PublishPlatformAdapter):
    """Safe base for real public-publishing adapters.

    It owns capability/credential checks and platform payload mapping. A concrete
    provider must explicitly implement its upload protocol before external writes
    are allowed; no mock success can be returned for a real platform.
    """

    platform_label = "Remote platform"

    def __init__(self, platform: PublishPlatform, account: PublishAccount) -> None:
        self.platform = platform
        self.account = account

    def configuration_status(self) -> tuple[bool, str, dict[str, Any]]:
        missing: list[str] = []
        if not self.platform.enabled:
            missing.append("platform_enabled")
        if not self.account.enabled:
            missing.append("account_enabled")
        if not self.platform.api_base_url:
            missing.append("api_base_url")
        if self.platform.auth_type in {"oauth2", "oauth2_pkce", "bearer_token"}:
            if not decrypt_secret(self.account.access_token_encrypted):
                missing.append("access_token")
        if self.account.token_expires_at:
            expiry = self.account.token_expires_at
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=UTC)
            if expiry <= datetime.now(UTC):
                missing.append("access_token_expired")
        return (
            not missing,
            "账号配置完整；仍需官方凭证端到端验证" if not missing else "发布账号配置不完整",
            {"platform": self.platform.code, "missing": missing},
        )

    def build_platform_payload(self, request: PublishRequest) -> dict[str, Any]:
        return {**request.common_payload, **request.platform_payload}

    async def publish_video(self, request: PublishRequest) -> PublishResult:
        configured, message, details = self.configuration_status()
        if not configured:
            raise PermanentPublishError(f"{message}: {', '.join(details['missing'])}")
        self.build_platform_payload(request)
        raise PermanentPublishError(
            f"{self.platform_label} 外部写入尚未使用真实凭证完成端到端验证，未执行发布"
        )

    async def get_publish_status(self, platform_post_id: str) -> PublishResult:
        raise PermanentPublishError(f"{self.platform_label} 状态查询尚未完成真实凭证验证")

    async def refresh_token(self) -> None:
        if not decrypt_secret(self.account.refresh_token_encrypted):
            raise PermanentPublishError("账号没有可用的 refresh_token，请重新连接 OAuth 账号")
        raise TemporaryPublishError(f"{self.platform_label} Token 刷新需通过官方 OAuth 配置验证")
