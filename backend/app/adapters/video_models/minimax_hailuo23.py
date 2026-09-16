import base64
import mimetypes
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from app.adapters.video_models.base import (
    GeneratedVideo,
    GenerationRequest,
    VideoModelAdapterError,
)
from app.adapters.video_models.configured import ConfiguredVideoModelAdapter
from app.adapters.video_models.minimax_client import MiniMaxClient
from app.core.config import get_settings
from app.core.security import decrypt_secret


class MiniMaxHailuo23Adapter(ConfiguredVideoModelAdapter):
    provider_label = "MiniMax Hailuo 2.3"
    deferred_polling = True
    task_failure_error_code = "MINIMAX_TASK_FAILED"
    task_failure_message = "MiniMax 视频生成失败"
    timeout_error_code = "MINIMAX_TIMEOUT"
    timeout_message = "MiniMax 视频生成超时"

    def __init__(self, model, *, client: MiniMaxClient | None = None) -> None:
        super().__init__(model)
        settings = get_settings()
        api_key = decrypt_secret(self.account.api_key_encrypted) or ""
        self.client = client or MiniMaxClient(
            base_url=self.base_url,
            api_key=api_key,
            timeout_seconds=settings.minimax_http_timeout_seconds,
        )

    @property
    def poll_interval_seconds(self) -> int:
        return max(1, get_settings().minimax_poll_interval_seconds)

    @property
    def generation_timeout_seconds(self) -> int:
        return max(1, get_settings().minimax_generation_timeout_seconds)

    def configuration_status(self) -> tuple[bool, str, dict[str, Any]]:
        missing: list[str] = []
        if not self.provider.enabled:
            missing.append("provider_enabled")
        if not self.account.enabled:
            missing.append("account_enabled")
        if not self.model.enabled:
            missing.append("model_enabled")
        parsed = urlparse(self.base_url)
        if parsed.scheme != "https" or not parsed.netloc:
            missing.append("https_api_base_url")
        if not decrypt_secret(self.account.api_key_encrypted):
            missing.append("api_key")
        if not self.model.model_id:
            missing.append("model_id")
        configured = not missing
        return (
            configured,
            (
                "MiniMax configuration is complete. Real API verification has not been performed."
                if configured
                else "MiniMax 配置不完整；未执行真实 API 验证"
            ),
            {
                "provider_code": self.provider.code,
                "credential_configured": bool(decrypt_secret(self.account.api_key_encrypted)),
                "http_client_ready": bool(parsed.scheme == "https" and parsed.netloc),
                "real_api_verified": False,
                "missing": missing,
            },
        )

    async def test_connection(self) -> dict[str, Any]:
        configured, message, details = self.configuration_status()
        return {"success": configured, "message": message, **details}

    def _validate_request(self, request: GenerationRequest, *, image: bool) -> None:
        prompt_rules = (self.model.capabilities or {}).get("prompt", {})
        prompt_required = bool(
            prompt_rules.get(
                "required_for_image_to_video" if image else "required_for_text_to_video",
                not image,
            )
        )
        if prompt_required and not request.prompt.strip():
            raise VideoModelAdapterError("MINIMAX_INVALID_PARAMETER", "MiniMax 视频描述不能为空")
        max_length = int(prompt_rules.get("max_length", 2000))
        if len(request.prompt) > max_length:
            raise VideoModelAdapterError("MINIMAX_INVALID_PARAMETER", "MiniMax 视频描述过长")
        matrix = (self.model.capabilities or {}).get("resolution_duration_matrix", {})
        if request.resolution and request.duration is not None:
            allowed = matrix.get(request.resolution)
            if isinstance(allowed, list) and request.duration not in allowed:
                raise VideoModelAdapterError(
                    "MINIMAX_INVALID_PARAMETER", "MiniMax 不支持当前分辨率与时长组合"
                )

    def _payload(self, request: GenerationRequest, *, image: bool) -> dict[str, Any]:
        self._validate_request(request, image=image)
        defaults = self.model.request_defaults or {}
        payload: dict[str, Any] = {
            "model": self.model.model_id,
            "prompt_optimizer": bool(defaults.get("prompt_optimizer", True)),
            "fast_pretreatment": bool(defaults.get("fast_pretreatment", False)),
        }
        if request.prompt:
            # Camera commands such as [Pan left] intentionally pass through unchanged.
            payload["prompt"] = request.prompt
        if request.duration is not None:
            payload["duration"] = request.duration
        if request.resolution:
            payload["resolution"] = request.resolution
        callback_url = self.config.get("callback_url")
        if callback_url:
            payload["callback_url"] = str(callback_url)
        if image:
            payload["first_frame_image"] = self._first_frame_image(request)
        return payload

    @staticmethod
    def _first_frame_image(request: GenerationRequest) -> str:
        if request.source_image_url and urlparse(request.source_image_url).scheme in {"http", "https"}:
            return request.source_image_url
        if request.source_image_path is None:
            raise VideoModelAdapterError("MINIMAX_INVALID_PARAMETER", "图生视频缺少参考图片")
        mime_type = mimetypes.guess_type(request.source_image_path.name)[0]
        if mime_type not in {"image/jpeg", "image/png", "image/webp"}:
            raise VideoModelAdapterError("MINIMAX_INVALID_PARAMETER", "参考图片格式不受支持")
        encoded = base64.b64encode(request.source_image_path.read_bytes()).decode("ascii")
        return f"data:{mime_type};base64,{encoded}"

    async def _create(self, request: GenerationRequest, *, image: bool) -> str:
        configured, message, details = self.configuration_status()
        if not configured:
            raise VideoModelAdapterError(
                "MINIMAX_AUTH_FAILED", f"{message}: {', '.join(details['missing'])}"
            )
        response = await self.client.create_video(self._payload(request, image=image))
        task_id = response.get("task_id")
        if not task_id:
            raise VideoModelAdapterError(
                "MINIMAX_SERVICE_UNAVAILABLE", "MiniMax 响应缺少任务 ID"
            )
        self._last_payload[str(task_id)] = response
        return str(task_id)

    async def create_text_to_video(self, request: GenerationRequest) -> str:
        return await self._create(request, image=False)

    async def create_image_to_video(self, request: GenerationRequest) -> str:
        return await self._create(request, image=True)

    async def get_task_status(self, provider_task_id: str) -> str:
        response = await self.client.query_video(provider_task_id)
        self._last_payload[provider_task_id] = response
        mapping = {
            "preparing": "pending",
            "queueing": "pending",
            "processing": "processing",
            "success": "success",
            "fail": "failed",
        }
        status = mapping.get(str(response.get("status", "")).lower())
        if status is None:
            raise VideoModelAdapterError(
                "MINIMAX_SERVICE_UNAVAILABLE", "MiniMax 返回了未知任务状态"
            )
        return status

    async def get_result(self, provider_task_id: str, work_dir: Path) -> GeneratedVideo:
        response = self._last_payload.get(provider_task_id)
        if not response or not response.get("file_id"):
            response = await self.client.query_video(provider_task_id)
            self._last_payload[provider_task_id] = response
        file_id = response.get("file_id")
        if not file_id:
            raise VideoModelAdapterError(
                "MINIMAX_DOWNLOAD_FAILED", "MiniMax 成功任务缺少文件 ID"
            )
        file_response = await self.client.retrieve_file(str(file_id))
        file_data = file_response.get("file")
        download_url = file_data.get("download_url") if isinstance(file_data, dict) else None
        if not download_url:
            raise VideoModelAdapterError(
                "MINIMAX_DOWNLOAD_FAILED", "MiniMax 文件响应缺少下载地址"
            )
        target = work_dir / f"{uuid.uuid4().hex}.mp4"
        await self.client.download_video(str(download_url), target)
        return GeneratedVideo(local_path=target, provider_task_id=provider_task_id)
