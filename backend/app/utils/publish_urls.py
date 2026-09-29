import re
from typing import Any
from urllib.parse import quote, urlsplit


_INSTAGRAM_USERNAME = re.compile(r"^[A-Za-z0-9._]+$")


def normalize_web_url(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    parsed = urlsplit(text)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        return None
    return text


def resolve_platform_url(platform_code: str, account: Any) -> str | None:
    """Resolve an account/channel homepage without calling a publishing API."""
    config = account.extra_config or {}
    code = platform_code.strip().lower()
    explicit_keys = {
        "instagram": ("instagram_profile_url", "profile_url", "platform_url"),
        "youtube": ("youtube_channel_url", "channel_url", "platform_url"),
        "x": ("x_profile_url", "profile_url", "platform_url"),
        "facebook": ("facebook_page_url", "page_url", "platform_url"),
    }.get(code, ("platform_url",))
    for key in explicit_keys:
        explicit = normalize_web_url(config.get(key))
        if explicit:
            return explicit

    identifier = str(account.account_identifier or "").strip()
    if code == "instagram":
        username = str(config.get("username") or identifier).strip().lstrip("@")
        if username and _INSTAGRAM_USERNAME.fullmatch(username):
            return f"https://www.instagram.com/{username}/"
    elif code == "youtube":
        handle = str(config.get("channel_handle") or config.get("handle") or "").strip()
        if not handle and identifier.startswith("@"):
            handle = identifier
        if handle:
            return f"https://www.youtube.com/@{quote(handle.lstrip('@'), safe='')}"
        channel_id = str(account.channel_id or config.get("channel_id") or "").strip()
        external_id = str(account.external_account_id or "").strip()
        if not channel_id and external_id.startswith("UC"):
            channel_id = external_id
        if channel_id:
            return f"https://www.youtube.com/channel/{quote(channel_id, safe='')}"
    elif code == "x":
        username = str(config.get("username") or identifier).strip().lstrip("@")
        if username:
            return f"https://x.com/{quote(username, safe='')}"
    elif code == "facebook":
        page_id = str(account.page_id or config.get("page_id") or "").strip()
        if page_id:
            return f"https://www.facebook.com/{quote(page_id, safe='')}"
    return None
