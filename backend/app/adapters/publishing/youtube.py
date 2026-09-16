from typing import Any

from app.adapters.publishing.base import PublishRequest
from app.adapters.publishing.configured import ConfiguredPublishAdapter


class YouTubePublishAdapter(ConfiguredPublishAdapter):
    platform_label = "YouTube Data API v3"

    def build_platform_payload(self, request: PublishRequest) -> dict[str, Any]:
        overrides = request.platform_payload
        snippet: dict[str, Any] = {
            "title": overrides.get("title", request.title),
            "description": overrides.get("description", request.description or request.content or ""),
            "tags": overrides.get("tags", request.tags),
        }
        if overrides.get("category_id"):
            snippet["categoryId"] = overrides["category_id"]
        status: dict[str, Any] = {
            "privacyStatus": overrides.get("privacy_status", "private"),
            "selfDeclaredMadeForKids": bool(overrides.get("self_declared_made_for_kids", False)),
            "containsSyntheticMedia": bool(overrides.get("contains_synthetic_media", True)),
        }
        if overrides.get("publish_at"):
            status["publishAt"] = overrides["publish_at"]
        return {"snippet": snippet, "status": status}
