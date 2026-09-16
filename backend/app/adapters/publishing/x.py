from typing import Any

from app.adapters.publishing.base import PublishRequest
from app.adapters.publishing.configured import ConfiguredPublishAdapter


class XPublishAdapter(ConfiguredPublishAdapter):
    platform_label = "X API v2"

    def build_platform_payload(self, request: PublishRequest) -> dict[str, Any]:
        text = request.platform_payload.get("content", request.content or request.description or "")
        payload: dict[str, Any] = {"text": text}
        if request.platform_payload.get("media_ids"):
            payload["media"] = {"media_ids": request.platform_payload["media_ids"]}
        return payload
