import re
from typing import Any
from urllib.parse import quote, urlsplit


_INSTAGRAM_USERNAME = re.compile(r"^[A-Za-z0-9._]+$")
_INSTAGRAM_SHORTCODE = re.compile(r"^[A-Za-z0-9_-]+$")
_INSTAGRAM_ACCOUNT_TYPES = {"BUSINESS", "CREATOR", "MEDIA_CREATOR", "PERSONAL"}


def normalize_web_url(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    parsed = urlsplit(text)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        return None
    return text


def instagram_profile_url(username: Any) -> str | None:
    value = str(username or "").strip().lstrip("@")
    if (
        not value
        or value.upper() in _INSTAGRAM_ACCOUNT_TYPES
        or not _INSTAGRAM_USERNAME.fullmatch(value)
    ):
        return None
    return f"https://www.instagram.com/{value}/"


def normalize_platform_url(platform_code: str, value: Any) -> str | None:
    url = normalize_web_url(value)
    if not url or str(platform_code or "").strip().lower() != "instagram":
        return url
    parsed = urlsplit(url)
    if parsed.hostname not in {"instagram.com", "www.instagram.com"}:
        return url
    username = next((part for part in parsed.path.split("/") if part), "")
    return url if instagram_profile_url(username) else None


def resolve_publish_url(
    platform_code: str,
    platform_post_id: Any,
    current_url: Any = None,
) -> str | None:
    """Return a canonical content URL without making another platform API call."""
    code = str(platform_code or "").strip().lower()
    post_id = str(platform_post_id or "").strip()
    current = normalize_web_url(current_url)

    if code == "instagram":
        if not current:
            return None
        parsed = urlsplit(current)
        parts = [part for part in parsed.path.split("/") if part]
        if (
            parsed.hostname not in {"instagram.com", "www.instagram.com"}
            or len(parts) < 2
            or parts[0].lower() not in {"p", "reel", "reels", "tv"}
            or not _INSTAGRAM_SHORTCODE.fullmatch(parts[1])
        ):
            return None
        shortcode = parts[1]
        if post_id.isdigit() and shortcode == post_id:
            return None
        return f"https://www.instagram.com/p/{quote(shortcode, safe='')}/"
    if code == "youtube":
        return (
            f"https://www.youtube.com/watch?v={quote(post_id, safe='')}"
            if post_id
            else current
        )

    # Mock and legacy internal results intentionally use application-relative URLs.
    relative = str(current_url or "").strip()
    return current or (relative if relative.startswith("/") else None)


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
        explicit = normalize_platform_url(code, config.get(key))
        if explicit:
            return explicit

    identifier = str(account.account_identifier or "").strip()
    if code == "instagram":
        candidates = (
            config.get("instagram_username"),
            config.get("ig_username"),
            config.get("username"),
            identifier,
            account.name,
        )
        for candidate in candidates:
            profile_url = instagram_profile_url(candidate)
            if profile_url:
                return profile_url
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
