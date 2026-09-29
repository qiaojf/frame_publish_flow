import asyncio
import ipaddress
import re
import time
from collections.abc import Awaitable, Callable
from typing import Any
from urllib.parse import quote, urlsplit

import httpx

from app.adapters.publishing.base import PermanentPublishError, PublishRequest, PublishResult
from app.adapters.publishing.configured import ConfiguredPublishAdapter
from app.core.logging import logger
from app.core.security import decrypt_secret
from app.models import PublishAccount, PublishPlatform
from app.utils.publish_urls import normalize_web_url, resolve_platform_url, resolve_publish_url


_API_VERSION_PATTERN = re.compile(r"^v\d+\.\d+$")
_TOKEN_PATTERN = re.compile(
    r"(?i)(access_token(?:%3D|=|[\"']?\s*:\s*[\"']?))([^&\s\"']+)"
)
_FAILED_CONTAINER_STATUSES = {"ERROR", "EXPIRED"}


class InstagramPublishError(PermanentPublishError):
    """Safe, structured details from one stage of the Instagram publish flow."""

    def __init__(
        self,
        error_code: str,
        message: str,
        *,
        stage: str,
        retryable: bool = False,
        http_status: int | None = None,
        meta_error_type: str | None = None,
        meta_error_code: int | str | None = None,
        meta_error_subcode: int | str | None = None,
        fbtrace_id: str | None = None,
        container_id: str | None = None,
    ) -> None:
        self.error_code = error_code
        self.stage = stage
        self.retryable = retryable
        self.http_status = http_status
        self.meta_error_type = meta_error_type
        self.meta_error_code = meta_error_code
        self.meta_error_subcode = meta_error_subcode
        self.fbtrace_id = fbtrace_id
        self.container_id = container_id
        self.details = {
            "platform": "instagram",
            "stage": stage,
            "error_code": error_code,
            "retryable": retryable,
            "http_status": http_status,
            "meta_error_type": meta_error_type,
            "meta_error_code": meta_error_code,
            "meta_error_subcode": meta_error_subcode,
            "fbtrace_id": fbtrace_id,
            "container_id": container_id,
        }
        context = [f"stage={stage}"]
        if http_status is not None:
            context.append(f"http_status={http_status}")
        if meta_error_type:
            context.append(f"meta_error_type={meta_error_type}")
        if meta_error_code is not None:
            context.append(f"meta_error_code={meta_error_code}")
        if meta_error_subcode is not None:
            context.append(f"meta_error_subcode={meta_error_subcode}")
        if fbtrace_id:
            context.append(f"fbtrace_id={fbtrace_id}")
        if container_id:
            context.append(f"container_id={container_id}")
        super().__init__(f"Instagram publish failed ({', '.join(context)}): {message}")


class _RetryableContainerStatusError(RuntimeError):
    pass


class InstagramPublishAdapter(ConfiguredPublishAdapter):
    platform_label = "Instagram Graph API"

    def __init__(
        self,
        platform: PublishPlatform,
        account: PublishAccount,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        super().__init__(platform, account)
        self._transport = transport
        self._sleep = sleep
        self._monotonic = monotonic

    @property
    def _config(self) -> dict[str, Any]:
        return {**(self.platform.extra_config or {}), **(self.account.extra_config or {})}

    @property
    def base_url(self) -> str:
        configured = self._config
        value = (
            configured.get("base_url")
            or configured.get("api_base_url")
            or self.platform.api_base_url
            or "https://graph.instagram.com"
        )
        return str(value).rstrip("/")

    @property
    def api_version(self) -> str:
        value = self._config.get("api_version") or self.platform.api_version or "v26.0"
        version = str(value).strip()
        return version if version.startswith("v") else f"v{version}"

    @property
    def ig_user_id(self) -> str:
        return str(self.account.ig_user_id or self._config.get("ig_user_id") or "").strip()

    @property
    def access_token(self) -> str:
        return decrypt_secret(self.account.access_token_encrypted) or ""

    def _positive_seconds(self, key: str, default: float) -> float:
        value = float(self._config.get(key, default))
        if value <= 0:
            raise ValueError(f"{key} must be greater than zero")
        return value

    @property
    def poll_interval_seconds(self) -> float:
        return self._positive_seconds("poll_interval_seconds", 5.0)

    @property
    def processing_timeout_seconds(self) -> float:
        return self._positive_seconds("processing_timeout_seconds", 300.0)

    @property
    def http_timeout_seconds(self) -> float:
        return self._positive_seconds("http_timeout_seconds", 30.0)

    @property
    def require_https_video_url(self) -> bool:
        value = self._config.get("require_https_video_url", True)
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() not in {"0", "false", "no", "off"}

    def configuration_status(self) -> tuple[bool, str, dict[str, Any]]:
        _, _, base_details = super().configuration_status()
        missing = list(base_details.get("missing", []))
        if self.base_url and "api_base_url" in missing:
            missing.remove("api_base_url")
        if not self.ig_user_id:
            missing.append("ig_user_id")
        if not _API_VERSION_PATTERN.fullmatch(self.api_version):
            missing.append("api_version_invalid")
        parsed_base_url = urlsplit(self.base_url)
        if parsed_base_url.scheme != "https" or not parsed_base_url.hostname:
            missing.append("api_base_url_invalid")
        for key, default in (
            ("poll_interval_seconds", 5.0),
            ("processing_timeout_seconds", 300.0),
            ("http_timeout_seconds", 30.0),
        ):
            try:
                self._positive_seconds(key, default)
            except (TypeError, ValueError):
                missing.append(f"{key}_invalid")
        missing = list(dict.fromkeys(missing))
        return (
            not missing,
            "Instagram 发布配置完整" if not missing else "Instagram 发布配置不完整",
            {
                "platform": self.platform.code,
                "missing": missing,
                "api_version": self.api_version,
                "base_url": self.base_url,
            },
        )

    @staticmethod
    def _sanitize(value: Any, access_token: str) -> str:
        text = str(value or "")
        if access_token:
            text = text.replace(access_token, "[REDACTED]")
        return _TOKEN_PATTERN.sub(r"\1[REDACTED]", text)

    def _error_from_response(
        self,
        response: httpx.Response,
        payload: dict[str, Any],
        *,
        error_code: str,
        stage: str,
        container_id: str | None = None,
    ) -> InstagramPublishError:
        raw_error = payload.get("error")
        meta_error = raw_error if isinstance(raw_error, dict) else {}
        message = self._sanitize(
            meta_error.get("message") or f"Instagram API returned HTTP {response.status_code}",
            self.access_token,
        )
        error = InstagramPublishError(
            error_code,
            message,
            stage=stage,
            http_status=response.status_code,
            meta_error_type=self._sanitize(meta_error.get("type"), self.access_token) or None,
            meta_error_code=meta_error.get("code"),
            meta_error_subcode=meta_error.get("error_subcode"),
            fbtrace_id=self._sanitize(meta_error.get("fbtrace_id"), self.access_token) or None,
            container_id=container_id,
        )
        logger.warning("instagram_api_error", **error.details, message=message)
        return error

    @staticmethod
    def _json_payload(response: httpx.Response) -> dict[str, Any]:
        try:
            payload = response.json()
        except ValueError:
            return {}
        return payload if isinstance(payload, dict) else {}

    def _endpoint(self, *resources: str) -> str:
        path = "/".join(quote(resource, safe="") for resource in resources)
        return f"{self.base_url}/{self.api_version}/{path}"

    def _validate_video_url(self, video_url: Any) -> str:
        if not isinstance(video_url, str) or not video_url.strip():
            raise InstagramPublishError(
                "INSTAGRAM_VIDEO_URL_REQUIRED",
                "Instagram video publishing requires platform_payload.video_url",
                stage="CREATE_CONTAINER",
            )
        value = video_url.strip()
        try:
            parsed = urlsplit(value)
            hostname = parsed.hostname
        except ValueError as exc:
            raise InstagramPublishError(
                "INSTAGRAM_VIDEO_URL_INVALID",
                "Instagram video_url must be a valid public HTTP(S) URL",
                stage="CREATE_CONTAINER",
            ) from exc
        if parsed.scheme not in {"http", "https"} or not hostname:
            raise InstagramPublishError(
                "INSTAGRAM_VIDEO_URL_INVALID",
                "Instagram video_url must be a valid public HTTP(S) URL",
                stage="CREATE_CONTAINER",
            )
        if self.require_https_video_url and parsed.scheme != "https":
            raise InstagramPublishError(
                "INSTAGRAM_VIDEO_URL_HTTPS_REQUIRED",
                "Instagram video_url must use HTTPS",
                stage="CREATE_CONTAINER",
            )
        if parsed.username or parsed.password:
            raise InstagramPublishError(
                "INSTAGRAM_VIDEO_URL_NOT_PUBLIC",
                "Instagram video_url must not require URL credentials",
                stage="CREATE_CONTAINER",
            )
        normalized_host = hostname.rstrip(".").lower()
        if normalized_host == "localhost" or normalized_host.endswith((".localhost", ".local")):
            raise InstagramPublishError(
                "INSTAGRAM_VIDEO_URL_NOT_PUBLIC",
                "Instagram video_url must be publicly reachable",
                stage="CREATE_CONTAINER",
            )
        try:
            address = ipaddress.ip_address(normalized_host)
        except ValueError:
            address = None
        if address and (
            address.is_private
            or address.is_loopback
            or address.is_link_local
            or address.is_reserved
            or address.is_unspecified
            or address.is_multicast
        ):
            raise InstagramPublishError(
                "INSTAGRAM_VIDEO_URL_NOT_PUBLIC",
                "Instagram video_url must be publicly reachable",
                stage="CREATE_CONTAINER",
            )
        return value

    @staticmethod
    def _as_boolean(value: Any) -> bool:
        if isinstance(value, str):
            return value.strip().lower() not in {"0", "false", "no", "off", ""}
        return bool(value)

    def build_platform_payload(self, request: PublishRequest) -> dict[str, Any]:
        publish_type = request.publish_type.strip().lower()
        if publish_type not in {"reel", "video"}:
            raise InstagramPublishError(
                "INSTAGRAM_PUBLISH_TYPE_UNSUPPORTED",
                "Instagram PoC only supports Reel publishing",
                stage="CREATE_CONTAINER",
            )
        caption_value = (
            request.platform_payload["caption"]
            if "caption" in request.platform_payload
            else request.content or request.description or ""
        )
        return {
            "media_type": "REELS",
            "video_url": self._validate_video_url(request.platform_payload.get("video_url")),
            "caption": "" if caption_value is None else str(caption_value),
            "share_to_feed": self._as_boolean(
                request.platform_payload.get("share_to_feed", True)
            ),
        }

    async def create_media_container(
        self,
        client: httpx.AsyncClient,
        payload: dict[str, Any],
    ) -> str:
        stage = "CREATE_CONTAINER"
        logger.info("instagram_create_container_started", platform="instagram", stage=stage)
        form = {
            "media_type": "REELS",
            "video_url": payload["video_url"],
            "caption": payload["caption"],
            "share_to_feed": "true" if payload["share_to_feed"] else "false",
            "access_token": self.access_token,
        }
        try:
            response = await client.post(self._endpoint(self.ig_user_id, "media"), data=form)
        except (httpx.TimeoutException, httpx.RequestError) as exc:
            raise InstagramPublishError(
                "CREATE_CONTAINER_RESULT_UNKNOWN",
                "Instagram media container request did not return a conclusive result",
                stage=stage,
            ) from exc
        response_payload = self._json_payload(response)
        if response.is_error or "error" in response_payload:
            raise self._error_from_response(
                response,
                response_payload,
                error_code="INSTAGRAM_CREATE_CONTAINER_FAILED",
                stage=stage,
            )
        container_id = response_payload.get("id")
        if not container_id:
            raise InstagramPublishError(
                "INSTAGRAM_CREATE_CONTAINER_INVALID_RESPONSE",
                "Instagram create container response did not include an id",
                stage=stage,
                http_status=response.status_code,
            )
        result = str(container_id)
        logger.info(
            "instagram_container_created",
            platform="instagram",
            stage=stage,
            container_id=result,
        )
        return result

    async def get_container_status(
        self,
        client: httpx.AsyncClient,
        container_id: str,
    ) -> dict[str, Any]:
        stage = "GET_CONTAINER_STATUS"
        try:
            response = await client.get(
                self._endpoint(container_id),
                params={
                    "fields": "status_code,status",
                    "access_token": self.access_token,
                },
            )
        except (httpx.TimeoutException, httpx.RequestError) as exc:
            raise _RetryableContainerStatusError("temporary Instagram status request failure") from exc
        if response.status_code >= 500:
            raise _RetryableContainerStatusError(
                f"temporary Instagram status HTTP {response.status_code}"
            )
        response_payload = self._json_payload(response)
        if response.is_error or "error" in response_payload:
            raise self._error_from_response(
                response,
                response_payload,
                error_code="INSTAGRAM_GET_CONTAINER_STATUS_FAILED",
                stage=stage,
                container_id=container_id,
            )
        return response_payload

    async def wait_for_container(
        self,
        client: httpx.AsyncClient,
        container_id: str,
    ) -> dict[str, Any]:
        deadline = self._monotonic() + self.processing_timeout_seconds
        first_attempt = True
        while first_attempt or self._monotonic() < deadline:
            first_attempt = False
            try:
                payload = await self.get_container_status(client, container_id)
            except _RetryableContainerStatusError:
                logger.warning(
                    "instagram_container_status_retry",
                    platform="instagram",
                    stage="GET_CONTAINER_STATUS",
                    container_id=container_id,
                )
            else:
                status_code = str(payload.get("status_code") or "").upper()
                logger.info(
                    "instagram_container_status",
                    platform="instagram",
                    stage="WAIT_CONTAINER",
                    container_id=container_id,
                    status_code=status_code or "UNKNOWN",
                )
                if status_code == "FINISHED":
                    return payload
                status_text = self._sanitize(payload.get("status"), self.access_token)
                if status_code in _FAILED_CONTAINER_STATUSES or status_text.lower().startswith("error"):
                    raise InstagramPublishError(
                        "INSTAGRAM_CONTAINER_PROCESSING_FAILED",
                        status_text or f"Instagram container entered {status_code}",
                        stage="WAIT_CONTAINER",
                        container_id=container_id,
                    )
            remaining = deadline - self._monotonic()
            if remaining <= 0:
                break
            await self._sleep(min(self.poll_interval_seconds, remaining))
        raise InstagramPublishError(
            "PROCESSING_TIMEOUT",
            "Instagram media container processing timed out",
            stage="WAIT_CONTAINER",
            container_id=container_id,
        )

    async def publish_media(
        self, client: httpx.AsyncClient, container_id: str
    ) -> tuple[str, str | None]:
        stage = "PUBLISH_MEDIA"
        logger.info(
            "instagram_publish_started",
            platform="instagram",
            stage=stage,
            container_id=container_id,
        )
        try:
            response = await client.post(
                self._endpoint(self.ig_user_id, "media_publish"),
                data={"creation_id": container_id, "access_token": self.access_token},
            )
        except (httpx.TimeoutException, httpx.RequestError) as exc:
            raise InstagramPublishError(
                "PUBLISH_RESULT_UNKNOWN",
                "Instagram media_publish result is unknown; do not retry blindly",
                stage=stage,
                container_id=container_id,
            ) from exc
        response_payload = self._json_payload(response)
        if response.is_error or "error" in response_payload:
            raise self._error_from_response(
                response,
                response_payload,
                error_code="INSTAGRAM_PUBLISH_MEDIA_FAILED",
                stage=stage,
                container_id=container_id,
            )
        media_id = response_payload.get("id")
        if not media_id:
            raise InstagramPublishError(
                "PUBLISH_RESULT_UNKNOWN",
                "Instagram media_publish response did not include a media id",
                stage=stage,
                http_status=response.status_code,
                container_id=container_id,
            )
        result = str(media_id)
        logger.info(
            "instagram_publish_succeeded",
            platform="instagram",
            stage=stage,
            container_id=container_id,
            media_id=result,
        )
        return result, normalize_web_url(
            response_payload.get("permalink") or response_payload.get("permalink_url")
        )

    async def publish_video(self, request: PublishRequest) -> PublishResult:
        configured, message, details = self.configuration_status()
        if not configured:
            raise InstagramPublishError(
                "INSTAGRAM_CONFIGURATION_INVALID",
                f"{message}: {', '.join(details['missing'])}",
                stage="CREATE_CONTAINER",
            )
        payload = self.build_platform_payload(request)
        timeout = httpx.Timeout(self.http_timeout_seconds)
        async with httpx.AsyncClient(timeout=timeout, transport=self._transport) as client:
            container_id = await self.create_media_container(client, payload)
            await self.wait_for_container(client, container_id)
            media_id, permalink = await self.publish_media(client, container_id)
        return PublishResult(
            status="success",
            platform_post_id=media_id,
            publish_url=resolve_publish_url("instagram", media_id, permalink),
            platform_url=resolve_platform_url("instagram", self.account),
            provider_container_id=container_id,
            metadata={"container_id": container_id, "media_id": media_id, "permalink": permalink},
        )
