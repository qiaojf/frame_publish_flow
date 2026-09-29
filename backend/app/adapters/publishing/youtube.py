import asyncio
import mimetypes
import re
import time
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import httpx
from sqlalchemy.orm import object_session

from app.adapters.publishing.base import PermanentPublishError, PublishRequest, PublishResult
from app.adapters.publishing.configured import ConfiguredPublishAdapter
from app.core.logging import logger
from app.core.security import decrypt_secret, encrypt_secret
from app.models import PublishAccount, PublishPlatform


YOUTUBE_UPLOAD_SCOPE = "https://www.googleapis.com/auth/youtube.upload"
YOUTUBE_READONLY_SCOPE = "https://www.googleapis.com/auth/youtube.readonly"
_REQUIRED_SCOPES = {YOUTUBE_UPLOAD_SCOPE, YOUTUBE_READONLY_SCOPE}
_TRANSIENT_STATUSES = {500, 502, 503, 504}
_PROCESSING_FAILURES = {"failed", "terminated"}
_SECRET_PATTERN = re.compile(
    r"(?i)((?:access|refresh)[_-]?token|client[_-]?secret|authorization)"
    r"(?:%3D|=|[\"']?\s*:\s*[\"']?)\s*([^&\s\"']+)"
)


class YouTubePublishError(PermanentPublishError):
    """A structured, token-safe failure from one YouTube publishing stage."""

    def __init__(
        self,
        error_code: str,
        message: str,
        *,
        stage: str,
        retryable: bool = False,
        http_status: int | None = None,
        reason: str | None = None,
        video_id: str | None = None,
    ) -> None:
        self.error_code = error_code
        self.stage = stage
        self.retryable = retryable
        self.http_status = http_status
        self.reason = reason
        self.video_id = video_id
        self.details = {
            "platform": "youtube",
            "stage": stage,
            "error_code": error_code,
            "retryable": retryable,
            "http_status": http_status,
            "reason": reason,
            "video_id": video_id,
        }
        context = [f"stage={stage}"]
        if http_status is not None:
            context.append(f"http_status={http_status}")
        if reason:
            context.append(f"reason={reason}")
        if video_id:
            context.append(f"video_id={video_id}")
        super().__init__(f"YouTube publish failed ({', '.join(context)}): {message}")


class YouTubePublishAdapter(ConfiguredPublishAdapter):
    platform_label = "YouTube Data API v3"

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
    def api_base_url(self) -> str:
        value = self._config.get("api_base_url") or self.platform.api_base_url
        return str(value or "https://www.googleapis.com/youtube/v3").rstrip("/")

    @property
    def upload_base_url(self) -> str:
        value = self._config.get("upload_base_url")
        return str(value or "https://www.googleapis.com/upload/youtube/v3").rstrip("/")

    @property
    def token_uri(self) -> str:
        value = self._config.get("token_uri")
        return str(value or "https://oauth2.googleapis.com/token")

    @property
    def client_id(self) -> str:
        return decrypt_secret(self.account.client_id_encrypted) or str(
            self._config.get("client_id") or ""
        ).strip()

    @property
    def client_secret(self) -> str:
        return decrypt_secret(self.account.client_secret_encrypted) or str(
            self._config.get("client_secret") or ""
        ).strip()

    @property
    def access_token(self) -> str:
        return decrypt_secret(self.account.access_token_encrypted) or ""

    @property
    def refresh_token_value(self) -> str:
        return decrypt_secret(self.account.refresh_token_encrypted) or ""

    @property
    def authorized_scopes(self) -> set[str]:
        raw: Any = self.account.authorized_scopes or self._config.get("scopes") or []
        if isinstance(raw, str):
            raw = raw.replace(",", " ").split()
        return {str(value).strip() for value in raw if str(value).strip()}

    def _positive_number(self, key: str, default: float) -> float:
        value = float(self._config.get(key, default))
        if value <= 0:
            raise ValueError(f"{key} must be greater than zero")
        return value

    @property
    def poll_interval_seconds(self) -> float:
        return self._positive_number("poll_interval_seconds", 5.0)

    @property
    def processing_timeout_seconds(self) -> float:
        return self._positive_number("processing_timeout_seconds", 600.0)

    @property
    def http_timeout_seconds(self) -> float:
        return self._positive_number("http_timeout_seconds", 60.0)

    @property
    def retry_backoff_seconds(self) -> float:
        return self._positive_number("retry_backoff_seconds", 1.0)

    @property
    def max_retries(self) -> int:
        value = int(self._config.get("max_retries", 5))
        if value < 0:
            raise ValueError("max_retries must not be negative")
        return value

    @property
    def upload_chunk_size(self) -> int:
        value = int(self._config.get("upload_chunk_size", 8 * 1024 * 1024))
        if value <= 0 or value % (256 * 1024) != 0:
            raise ValueError("upload_chunk_size must be a positive multiple of 256 KiB")
        return value

    def _token_expired(self) -> bool:
        expiry = self.account.token_expires_at
        if expiry is None:
            return False
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=UTC)
        return expiry <= datetime.now(UTC) + timedelta(seconds=30)

    def configuration_status(self) -> tuple[bool, str, dict[str, Any]]:
        _, _, base_details = super().configuration_status()
        missing = list(base_details.get("missing", []))
        refresh_ready = bool(self.client_id and self.client_secret and self.refresh_token_value)
        if refresh_ready:
            missing = [item for item in missing if item not in {"access_token", "access_token_expired"}]
        if not self.access_token and not refresh_ready:
            missing.append("access_token_or_refresh_token")
        if not self.client_id:
            missing.append("client_id")
        if not self.client_secret:
            missing.append("client_secret")
        if not self.refresh_token_value:
            missing.append("refresh_token")
        missing_scopes = sorted(_REQUIRED_SCOPES - self.authorized_scopes)
        if missing_scopes:
            missing.append("authorized_scopes")
        for key, default in (
            ("poll_interval_seconds", 5.0),
            ("processing_timeout_seconds", 600.0),
            ("http_timeout_seconds", 60.0),
            ("retry_backoff_seconds", 1.0),
        ):
            try:
                self._positive_number(key, default)
            except (TypeError, ValueError):
                missing.append(f"{key}_invalid")
        try:
            self.upload_chunk_size
        except (TypeError, ValueError):
            missing.append("upload_chunk_size_invalid")
        try:
            self.max_retries
        except (TypeError, ValueError):
            missing.append("max_retries_invalid")
        for key, value in (
            ("api_base_url", self.api_base_url),
            ("upload_base_url", self.upload_base_url),
            ("token_uri", self.token_uri),
        ):
            parsed = urlsplit(value)
            if parsed.scheme not in {"http", "https"} or not parsed.hostname:
                missing.append(f"{key}_invalid")
        missing = list(dict.fromkeys(missing))
        return (
            not missing,
            "YouTube 发布配置完整" if not missing else "YouTube 发布配置不完整",
            {
                "platform": self.platform.code,
                "missing": missing,
                "missing_scopes": missing_scopes,
            },
        )

    def build_platform_payload(self, request: PublishRequest) -> dict[str, Any]:
        overrides = {**request.overrides, **request.platform_payload}
        title = str(overrides.get("title", request.title) or "").strip()
        description = str(
            overrides.get("description", request.description or request.content or "") or ""
        )
        tags = overrides.get("tags", request.tags)
        if not isinstance(tags, list):
            raise YouTubePublishError(
                "YOUTUBE_METADATA_INVALID", "tags 必须是字符串数组", stage="LOAD_CONFIG"
            )
        privacy_status = str(overrides.get("privacy_status", "private"))
        if not title or len(title) > 100:
            raise YouTubePublishError(
                "YOUTUBE_METADATA_INVALID", "标题必填且不能超过 100 个字符", stage="LOAD_CONFIG"
            )
        if len(description) > 5000 or any(not isinstance(tag, str) for tag in tags):
            raise YouTubePublishError(
                "YOUTUBE_METADATA_INVALID", "描述或标签不符合 YouTube 元数据要求", stage="LOAD_CONFIG"
            )
        if privacy_status not in {"private", "unlisted", "public"}:
            raise YouTubePublishError(
                "YOUTUBE_METADATA_INVALID", "privacy_status 必须是 private、unlisted 或 public",
                stage="LOAD_CONFIG",
            )
        snippet: dict[str, Any] = {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": str(overrides.get("category_id") or "22"),
        }
        status = {
            "privacyStatus": privacy_status,
            "selfDeclaredMadeForKids": bool(overrides.get("self_declared_made_for_kids", False)),
            "containsSyntheticMedia": bool(overrides.get("contains_synthetic_media", True)),
        }
        return {"snippet": snippet, "status": status}

    def _safe_text(self, value: Any) -> str:
        text = str(value or "YouTube API 请求失败")
        for secret in (
            self.access_token,
            self.refresh_token_value,
            self.client_id,
            self.client_secret,
        ):
            if secret:
                text = text.replace(secret, "[REDACTED]")
        text = re.sub(r"(?i)Bearer\s+[^\s,;]+", "Bearer [REDACTED]", text)
        return _SECRET_PATTERN.sub(lambda match: f"{match.group(1)}=[REDACTED]", text)[:400]

    @staticmethod
    def _error_payload(response: httpx.Response) -> tuple[str | None, str]:
        try:
            payload = response.json()
        except ValueError:
            return None, f"YouTube API 返回 HTTP {response.status_code}"
        error = payload.get("error") if isinstance(payload, dict) else None
        if isinstance(error, str):
            return error, str(payload.get("error_description") or error)
        if not isinstance(error, dict):
            return None, f"YouTube API 返回 HTTP {response.status_code}"
        reason = None
        errors = error.get("errors")
        if isinstance(errors, list) and errors and isinstance(errors[0], dict):
            reason = errors[0].get("reason")
        return str(reason) if reason else None, str(error.get("message") or "YouTube API 请求失败")

    def _api_error(
        self,
        response: httpx.Response,
        *,
        stage: str,
        video_id: str | None = None,
    ) -> YouTubePublishError:
        reason, message = self._error_payload(response)
        normalized = str(reason or "")
        mapping = {
            "invalid_grant": ("YOUTUBE_REAUTH_REQUIRED", False),
            "insufficientPermissions": ("YOUTUBE_SCOPE_INSUFFICIENT", False),
            "youtubeSignupRequired": ("YOUTUBE_CHANNEL_REQUIRED", False),
            "quotaExceeded": ("QUOTA_EXCEEDED", False),
            "dailyLimitExceeded": ("QUOTA_EXCEEDED", False),
        }
        error_code, retryable = mapping.get(normalized, ("", False))
        if not error_code:
            if response.status_code == 400:
                error_code = "YOUTUBE_INVALID_REQUEST"
            elif response.status_code == 401:
                error_code = "YOUTUBE_UNAUTHORIZED"
            elif response.status_code == 403:
                error_code = "YOUTUBE_FORBIDDEN"
            elif response.status_code == 404:
                error_code = "YOUTUBE_VIDEO_NOT_FOUND"
            elif response.status_code >= 500:
                error_code, retryable = "YOUTUBE_TEMPORARY_FAILURE", True
            else:
                error_code = "YOUTUBE_API_ERROR"
        return YouTubePublishError(
            error_code,
            self._safe_text(message),
            stage=stage,
            retryable=retryable,
            http_status=response.status_code,
            reason=normalized or None,
            video_id=video_id,
        )

    def _network_error(
        self, exc: Exception, *, stage: str, video_id: str | None = None
    ) -> YouTubePublishError:
        return YouTubePublishError(
            "YOUTUBE_NETWORK_ERROR",
            self._safe_text(exc),
            stage=stage,
            retryable=True,
            video_id=video_id,
        )

    async def _refresh_access_token(self, client: httpx.AsyncClient) -> str:
        if not self.client_id or not self.client_secret or not self.refresh_token_value:
            raise YouTubePublishError(
                "YOUTUBE_REAUTH_REQUIRED",
                "缺少 client_id、client_secret 或 refresh_token，请重新授权",
                stage="REFRESH_TOKEN",
            )
        try:
            response = await client.post(
                self.token_uri,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "refresh_token": self.refresh_token_value,
                    "grant_type": "refresh_token",
                },
            )
        except httpx.RequestError as exc:
            raise self._network_error(exc, stage="REFRESH_TOKEN") from exc
        if response.is_error:
            raise self._api_error(response, stage="REFRESH_TOKEN")
        try:
            payload = response.json()
        except ValueError as exc:
            raise YouTubePublishError(
                "YOUTUBE_TOKEN_RESPONSE_INVALID", "Token 刷新响应不是合法 JSON", stage="REFRESH_TOKEN"
            ) from exc
        access_token = str(payload.get("access_token") or "").strip()
        if not access_token:
            raise YouTubePublishError(
                "YOUTUBE_TOKEN_RESPONSE_INVALID", "Token 刷新响应缺少 access_token",
                stage="REFRESH_TOKEN",
            )
        self.account.access_token_encrypted = encrypt_secret(access_token)
        new_refresh_token = str(payload.get("refresh_token") or "").strip()
        if new_refresh_token:
            self.account.refresh_token_encrypted = encrypt_secret(new_refresh_token)
        expires_in = int(payload.get("expires_in") or 3600)
        self.account.token_expires_at = datetime.now(UTC) + timedelta(seconds=max(1, expires_in))
        session = object_session(self.account)
        if session is not None:
            session.commit()
        logger.info("youtube_access_token_refreshed", account_id=str(self.account.id))
        return access_token

    async def refresh_token(self) -> None:
        async with httpx.AsyncClient(
            transport=self._transport, timeout=self.http_timeout_seconds
        ) as client:
            await self._refresh_access_token(client)

    def _validate_video_file(self, path: Path) -> tuple[int, str]:
        try:
            is_file = path.is_file()
        except OSError:
            is_file = False
        if not is_file:
            raise YouTubePublishError(
                "YOUTUBE_FILE_NOT_FOUND", "本地视频文件不存在", stage="VALIDATE_FILE"
            )
        try:
            size = path.stat().st_size
            with path.open("rb") as handle:
                handle.read(1)
        except OSError as exc:
            raise YouTubePublishError(
                "YOUTUBE_FILE_UNREADABLE", "本地视频文件不可读取", stage="VALIDATE_FILE"
            ) from exc
        if size <= 0:
            raise YouTubePublishError(
                "YOUTUBE_FILE_EMPTY", "本地视频文件为空", stage="VALIDATE_FILE"
            )
        mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        return size, mime_type

    async def _post_upload_session(
        self,
        client: httpx.AsyncClient,
        *,
        access_token: str,
        payload: dict[str, Any],
        file_size: int,
        mime_type: str,
    ) -> str:
        url = f"{self.upload_base_url}/videos"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8",
            "X-Upload-Content-Length": str(file_size),
            "X-Upload-Content-Type": mime_type,
        }
        attempt = 0
        auth_refreshed = False
        while True:
            try:
                response = await client.post(
                    url,
                    params={"uploadType": "resumable", "part": "snippet,status"},
                    headers=headers,
                    json=payload,
                )
            except httpx.RequestError as exc:
                if attempt >= self.max_retries:
                    raise self._network_error(exc, stage="CREATE_UPLOAD") from exc
                await self._sleep(self.retry_backoff_seconds * (2**attempt))
                attempt += 1
                continue
            if response.status_code == 401 and not auth_refreshed:
                access_token = await self._refresh_access_token(client)
                headers["Authorization"] = f"Bearer {access_token}"
                auth_refreshed = True
                continue
            if response.status_code in _TRANSIENT_STATUSES and attempt < self.max_retries:
                await self._sleep(self.retry_backoff_seconds * (2**attempt))
                attempt += 1
                continue
            if response.is_error:
                raise self._api_error(response, stage="CREATE_UPLOAD")
            upload_url = response.headers.get("Location")
            if not upload_url:
                raise YouTubePublishError(
                    "YOUTUBE_UPLOAD_SESSION_INVALID",
                    "可恢复上传响应缺少 Location",
                    stage="CREATE_UPLOAD",
                )
            return upload_url

    @staticmethod
    def _uploaded_offset(response: httpx.Response) -> int:
        matched = re.search(r"bytes=\d+-(\d+)", response.headers.get("Range", ""))
        return int(matched.group(1)) + 1 if matched else 0

    async def _query_upload_offset(
        self,
        client: httpx.AsyncClient,
        upload_url: str,
        *,
        access_token: str,
        file_size: int,
    ) -> tuple[int, dict[str, Any] | None]:
        response = await client.put(
            upload_url,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Length": "0",
                "Content-Range": f"bytes */{file_size}",
            },
            content=b"",
        )
        if response.status_code == 308:
            return self._uploaded_offset(response), None
        if response.is_error:
            raise self._api_error(response, stage="UPLOAD_VIDEO")
        try:
            return file_size, response.json()
        except ValueError as exc:
            raise YouTubePublishError(
                "YOUTUBE_UPLOAD_RESPONSE_INVALID",
                "上传完成响应不是合法 JSON",
                stage="GET_VIDEO_ID",
            ) from exc

    def _report_progress(self, request: PublishRequest, uploaded: int, total: int) -> None:
        progress = min(100, max(0, int(uploaded * 100 / total)))
        logger.info("youtube_upload_progress", progress=progress)
        if request.progress_callback is None:
            return
        try:
            request.progress_callback(progress)
        except Exception:
            logger.warning("youtube_progress_callback_failed", progress=progress)

    async def _upload_video(
        self,
        client: httpx.AsyncClient,
        request: PublishRequest,
        upload_url: str,
        *,
        access_token: str,
        file_size: int,
        mime_type: str,
    ) -> dict[str, Any]:
        offset = 0
        with request.video_path.open("rb") as handle:
            while offset < file_size:
                handle.seek(offset)
                chunk = handle.read(min(self.upload_chunk_size, file_size - offset))
                end = offset + len(chunk) - 1
                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": mime_type,
                    "Content-Length": str(len(chunk)),
                    "Content-Range": f"bytes {offset}-{end}/{file_size}",
                }
                response: httpx.Response | None = None
                for attempt in range(self.max_retries + 1):
                    try:
                        response = await client.put(upload_url, headers=headers, content=chunk)
                    except httpx.RequestError as exc:
                        if attempt >= self.max_retries:
                            raise self._network_error(exc, stage="UPLOAD_VIDEO") from exc
                        await self._sleep(self.retry_backoff_seconds * (2**attempt))
                        try:
                            offset, completed = await self._query_upload_offset(
                                client,
                                upload_url,
                                access_token=access_token,
                                file_size=file_size,
                            )
                        except (httpx.RequestError, YouTubePublishError):
                            continue
                        if completed is not None:
                            self._report_progress(request, file_size, file_size)
                            return completed
                        break
                    if response.status_code == 401:
                        access_token = await self._refresh_access_token(client)
                        headers["Authorization"] = f"Bearer {access_token}"
                        try:
                            response = await client.put(upload_url, headers=headers, content=chunk)
                        except httpx.RequestError as exc:
                            raise self._network_error(exc, stage="UPLOAD_VIDEO") from exc
                    if response.status_code in _TRANSIENT_STATUSES:
                        if attempt >= self.max_retries:
                            raise self._api_error(response, stage="UPLOAD_VIDEO")
                        await self._sleep(self.retry_backoff_seconds * (2**attempt))
                        try:
                            offset, completed = await self._query_upload_offset(
                                client,
                                upload_url,
                                access_token=access_token,
                                file_size=file_size,
                            )
                        except (httpx.RequestError, YouTubePublishError):
                            continue
                        if completed is not None:
                            self._report_progress(request, file_size, file_size)
                            return completed
                        break
                    break
                if response is None or response.status_code in _TRANSIENT_STATUSES:
                    continue
                if response.status_code == 308:
                    offset = self._uploaded_offset(response)
                    self._report_progress(request, offset, file_size)
                    continue
                if response.is_error:
                    raise self._api_error(response, stage="UPLOAD_VIDEO")
                try:
                    payload = response.json()
                except ValueError as exc:
                    raise YouTubePublishError(
                        "YOUTUBE_UPLOAD_RESPONSE_INVALID",
                        "上传完成响应不是合法 JSON",
                        stage="GET_VIDEO_ID",
                    ) from exc
                self._report_progress(request, file_size, file_size)
                return payload
        raise YouTubePublishError(
            "YOUTUBE_UPLOAD_RESPONSE_INVALID", "上传结束但未获得视频响应", stage="GET_VIDEO_ID"
        )

    async def _fetch_processing_status(
        self,
        client: httpx.AsyncClient,
        video_id: str,
        *,
        access_token: str,
        allow_auth_refresh: bool = True,
    ) -> tuple[str, str | None]:
        try:
            response = await client.get(
                f"{self.api_base_url}/videos",
                params={"part": "processingDetails,status", "id": video_id},
                headers={"Authorization": f"Bearer {access_token}"},
            )
        except httpx.RequestError as exc:
            raise self._network_error(exc, stage="CHECK_PROCESSING", video_id=video_id) from exc
        if response.status_code == 401 and allow_auth_refresh:
            refreshed_token = await self._refresh_access_token(client)
            return await self._fetch_processing_status(
                client,
                video_id,
                access_token=refreshed_token,
                allow_auth_refresh=False,
            )
        if response.is_error:
            raise self._api_error(response, stage="CHECK_PROCESSING", video_id=video_id)
        try:
            items = response.json().get("items", [])
        except (AttributeError, ValueError) as exc:
            raise YouTubePublishError(
                "YOUTUBE_STATUS_RESPONSE_INVALID",
                "视频状态响应不是合法 JSON",
                stage="CHECK_PROCESSING",
                video_id=video_id,
            ) from exc
        if not items:
            raise YouTubePublishError(
                "YOUTUBE_VIDEO_NOT_FOUND",
                "YouTube 未返回对应视频",
                stage="CHECK_PROCESSING",
                http_status=404,
                video_id=video_id,
            )
        details = items[0].get("processingDetails") or {}
        status = str(details.get("processingStatus") or "processing").lower()
        failure_reason = details.get("processingFailureReason")
        return status, str(failure_reason) if failure_reason else None

    async def _wait_for_processing(
        self,
        client: httpx.AsyncClient,
        video_id: str,
        *,
        access_token: str,
    ) -> PublishResult:
        started = self._monotonic()
        while True:
            access_token = self.access_token or access_token
            try:
                status, failure_reason = await self._fetch_processing_status(
                    client, video_id, access_token=access_token
                )
            except YouTubePublishError as exc:
                if exc.retryable and self._monotonic() - started < self.processing_timeout_seconds:
                    await self._sleep(self.poll_interval_seconds)
                    continue
                raise
            logger.info(
                "youtube_processing_status",
                video_id=video_id,
                processing_status=status,
                processing_failure_reason=failure_reason,
            )
            if status == "succeeded":
                logger.info("youtube_publish_completed", video_id=video_id)
                return PublishResult(
                    status="success",
                    platform_post_id=video_id,
                    platform_post_url=f"https://www.youtube.com/watch?v={video_id}",
                    metadata={"video_id": video_id, "processing_status": status},
                )
            if status in _PROCESSING_FAILURES:
                code = (
                    "YOUTUBE_PROCESSING_FAILED"
                    if status == "failed"
                    else "YOUTUBE_PROCESSING_TERMINATED"
                )
                raise YouTubePublishError(
                    code,
                    (
                        f"YouTube 视频处理状态为 {status}"
                        + (f"，原因：{failure_reason}" if failure_reason else "")
                    ),
                    stage="CHECK_PROCESSING",
                    reason=failure_reason or status,
                    video_id=video_id,
                )
            if self._monotonic() - started >= self.processing_timeout_seconds:
                raise YouTubePublishError(
                    "PROCESSING_TIMEOUT",
                    "YouTube 视频处理超时；已保留 video_id，重试时只查询状态，不会重复上传",
                    stage="CHECK_PROCESSING",
                    retryable=True,
                    video_id=video_id,
                )
            await self._sleep(self.poll_interval_seconds)

    async def publish_video(self, request: PublishRequest) -> PublishResult:
        logger.info("youtube_publish_started")
        configured, message, details = self.configuration_status()
        if not configured:
            raise YouTubePublishError(
                "YOUTUBE_CONFIGURATION_INVALID",
                f"{message}: {', '.join(details['missing'])}",
                stage="LOAD_CONFIG",
            )
        payload = self.build_platform_payload(request)
        async with httpx.AsyncClient(
            transport=self._transport, timeout=self.http_timeout_seconds
        ) as client:
            logger.info("youtube_oauth_credentials_loaded", account_id=str(self.account.id))
            access_token = self.access_token
            if not access_token or self._token_expired():
                access_token = await self._refresh_access_token(client)
            if request.existing_platform_post_id:
                self._report_progress(request, 1, 1)
                return await self._wait_for_processing(
                    client, request.existing_platform_post_id, access_token=access_token
                )
            file_size, mime_type = self._validate_video_file(request.video_path)
            logger.info("youtube_upload_started", file_size=file_size, mime_type=mime_type)
            self._report_progress(request, 0, file_size)
            upload_url = await self._post_upload_session(
                client,
                access_token=access_token,
                payload=payload,
                file_size=file_size,
                mime_type=mime_type,
            )
            access_token = self.access_token or access_token
            uploaded = await self._upload_video(
                client,
                request,
                upload_url,
                access_token=access_token,
                file_size=file_size,
                mime_type=mime_type,
            )
            access_token = self.access_token or access_token
            video_id = str(uploaded.get("id") or "").strip()
            if not video_id:
                raise YouTubePublishError(
                    "YOUTUBE_VIDEO_ID_MISSING",
                    "上传完成响应缺少 video_id",
                    stage="GET_VIDEO_ID",
                )
            logger.info("youtube_upload_completed", video_id=video_id)
            return await self._wait_for_processing(client, video_id, access_token=access_token)

    async def get_publish_status(self, platform_post_id: str) -> PublishResult:
        video_id = str(platform_post_id).strip()
        if not video_id:
            raise YouTubePublishError(
                "YOUTUBE_VIDEO_ID_MISSING", "video_id 不能为空", stage="CHECK_PROCESSING"
            )
        async with httpx.AsyncClient(
            transport=self._transport, timeout=self.http_timeout_seconds
        ) as client:
            access_token = self.access_token
            if not access_token or self._token_expired():
                access_token = await self._refresh_access_token(client)
            status, failure_reason = await self._fetch_processing_status(
                client, video_id, access_token=access_token
            )
        if status == "succeeded":
            return PublishResult(
                status="success",
                platform_post_id=video_id,
                platform_post_url=f"https://www.youtube.com/watch?v={video_id}",
                metadata={"video_id": video_id, "processing_status": status},
            )
        if status in _PROCESSING_FAILURES:
            code = (
                "YOUTUBE_PROCESSING_FAILED"
                if status == "failed"
                else "YOUTUBE_PROCESSING_TERMINATED"
            )
            raise YouTubePublishError(
                code,
                (
                    f"YouTube 视频处理状态为 {status}"
                    + (f"，原因：{failure_reason}" if failure_reason else "")
                ),
                stage="CHECK_PROCESSING",
                reason=failure_reason or status,
                video_id=video_id,
            )
        return PublishResult(
            status="processing",
            platform_post_id=video_id,
            platform_post_url=f"https://www.youtube.com/watch?v={video_id}",
            metadata={"video_id": video_id, "processing_status": status},
        )
