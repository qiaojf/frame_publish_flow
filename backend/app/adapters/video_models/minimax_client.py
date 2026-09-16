from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import httpx

from app.adapters.video_models.base import VideoModelAdapterError
from app.core.logging import logger


class MiniMaxClient:
    """Small async client for MiniMax's create/query/retrieve API chain.

    The client deliberately exposes only sanitized project errors. Authentication
    headers and response bodies are never included in exceptions or logs.
    """

    _BUSINESS_ERRORS: dict[int, tuple[str, str, bool]] = {
        1000: ("MINIMAX_SERVICE_UNAVAILABLE", "MiniMax 服务暂时不可用", True),
        1001: ("MINIMAX_TIMEOUT", "MiniMax 请求超时", True),
        1002: ("MINIMAX_RATE_LIMITED", "MiniMax 请求频率受限，请稍后重试", True),
        1004: ("MINIMAX_AUTH_FAILED", "MiniMax API Key 无效或无权访问", False),
        1008: ("MINIMAX_INSUFFICIENT_BALANCE", "MiniMax 账号余额不足", False),
        1024: ("MINIMAX_SERVICE_UNAVAILABLE", "MiniMax 服务暂时不可用", True),
        1026: ("MINIMAX_INVALID_PARAMETER", "MiniMax 拒绝了输入内容", False),
        1027: ("MINIMAX_INVALID_PARAMETER", "MiniMax 生成内容未通过安全检查", False),
        1033: ("MINIMAX_SERVICE_UNAVAILABLE", "MiniMax 服务暂时不可用", True),
        1039: ("MINIMAX_RATE_LIMITED", "MiniMax 账号当前请求额度受限", True),
        1041: ("MINIMAX_RATE_LIMITED", "MiniMax 并发请求数已达上限", True),
        1042: ("MINIMAX_INVALID_PARAMETER", "MiniMax 检测到无效输入字符", False),
    }

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        timeout_seconds: float,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = httpx.Timeout(timeout_seconds)
        self.transport = transport

    @property
    def headers(self) -> dict[str, str]:
        return {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _url(self, path: str) -> str:
        return urljoin(f"{self.base_url}/", path.lstrip("/"))

    @staticmethod
    def _http_error(status_code: int) -> VideoModelAdapterError:
        if status_code in {401, 403}:
            return VideoModelAdapterError(
                "MINIMAX_AUTH_FAILED", "MiniMax API Key 无效或无权访问"
            )
        if status_code == 402:
            return VideoModelAdapterError(
                "MINIMAX_INSUFFICIENT_BALANCE", "MiniMax 账号余额不足"
            )
        if status_code == 429:
            return VideoModelAdapterError(
                "MINIMAX_RATE_LIMITED", "MiniMax 请求频率受限，请稍后重试", retryable=True
            )
        if status_code in {400, 404, 409, 422}:
            return VideoModelAdapterError(
                "MINIMAX_INVALID_PARAMETER", "MiniMax 请求参数无效"
            )
        return VideoModelAdapterError(
            "MINIMAX_SERVICE_UNAVAILABLE", "MiniMax 服务暂时不可用", retryable=True
        )

    def _validate_business_response(self, payload: dict[str, Any]) -> dict[str, Any]:
        base_resp = payload.get("base_resp")
        if not isinstance(base_resp, dict):
            raise VideoModelAdapterError(
                "MINIMAX_SERVICE_UNAVAILABLE", "MiniMax 返回了无法识别的响应"
            )
        try:
            status_code = int(base_resp.get("status_code", -1))
        except (TypeError, ValueError):
            status_code = -1
        if status_code == 0:
            return payload
        error_code, message, retryable = self._BUSINESS_ERRORS.get(
            status_code,
            ("MINIMAX_SERVICE_UNAVAILABLE", "MiniMax 服务暂时不可用", True),
        )
        logger.warning("minimax_business_error", provider_status_code=status_code)
        raise VideoModelAdapterError(error_code, message, retryable=retryable)

    async def _request_json(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                transport=self.transport,
                follow_redirects=True,
            ) as client:
                response = await client.request(
                    method,
                    self._url(path),
                    params=params,
                    json=json,
                    headers=self.headers,
                )
        except httpx.TimeoutException as exc:
            raise VideoModelAdapterError(
                "MINIMAX_TIMEOUT", "MiniMax 请求超时", retryable=True
            ) from exc
        except httpx.RequestError as exc:
            raise VideoModelAdapterError(
                "MINIMAX_SERVICE_UNAVAILABLE", "无法连接 MiniMax 服务", retryable=True
            ) from exc
        if not response.is_success:
            logger.warning("minimax_http_error", http_status=response.status_code)
            raise self._http_error(response.status_code)
        try:
            payload = response.json()
        except ValueError as exc:
            raise VideoModelAdapterError(
                "MINIMAX_SERVICE_UNAVAILABLE", "MiniMax 返回了无法识别的响应"
            ) from exc
        if not isinstance(payload, dict):
            raise VideoModelAdapterError(
                "MINIMAX_SERVICE_UNAVAILABLE", "MiniMax 返回了无法识别的响应"
            )
        return self._validate_business_response(payload)

    async def create_video(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._request_json("POST", "/v1/video_generation", json=payload)

    async def query_video(self, task_id: str) -> dict[str, Any]:
        return await self._request_json(
            "GET", "/v1/query/video_generation", params={"task_id": task_id}
        )

    async def retrieve_file(self, file_id: str) -> dict[str, Any]:
        return await self._request_json(
            "GET", "/v1/files/retrieve", params={"file_id": file_id}
        )

    async def download_video(self, download_url: str, target: Path) -> Path:
        target.parent.mkdir(parents=True, exist_ok=True)
        partial = target.with_suffix(f"{target.suffix}.part")
        partial.unlink(missing_ok=True)
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                transport=self.transport,
                follow_redirects=True,
            ) as client:
                async with client.stream(
                    "GET", download_url, headers={"Accept": "video/mp4,video/*"}
                ) as response:
                    if not response.is_success:
                        raise VideoModelAdapterError(
                            "MINIMAX_DOWNLOAD_FAILED", "MiniMax 视频下载失败"
                        )
                    with partial.open("wb") as handle:
                        async for chunk in response.aiter_bytes():
                            handle.write(chunk)
            if not partial.exists() or partial.stat().st_size == 0:
                raise VideoModelAdapterError(
                    "MINIMAX_DOWNLOAD_FAILED", "MiniMax 返回了空的视频文件"
                )
            partial.replace(target)
            return target
        except VideoModelAdapterError:
            partial.unlink(missing_ok=True)
            raise
        except (httpx.HTTPError, OSError) as exc:
            partial.unlink(missing_ok=True)
            raise VideoModelAdapterError(
                "MINIMAX_DOWNLOAD_FAILED", "MiniMax 视频下载失败", retryable=True
            ) from exc
