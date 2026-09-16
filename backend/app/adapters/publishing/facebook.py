from typing import Any

from app.adapters.publishing.base import PublishRequest
from app.adapters.publishing.configured import ConfiguredPublishAdapter


class FacebookPublishAdapter(ConfiguredPublishAdapter):
    platform_label = "Facebook Graph API / Page"

    def build_platform_payload(self, request: PublishRequest) -> dict[str, Any]:
        overrides = request.platform_payload
        payload: dict[str, Any] = {
            "title": overrides.get("title", request.title),
            "description": overrides.get("description", request.description or request.content or ""),
            "published": not bool(overrides.get("publish_at")),
        }
        if overrides.get("publish_at"):
            payload["scheduled_publish_time"] = overrides["publish_at"]
        return payload
