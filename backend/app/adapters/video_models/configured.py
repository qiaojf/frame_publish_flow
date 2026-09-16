import base64
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import httpx

from app.adapters.video_models.base import GeneratedVideo, GenerationRequest, VideoModelAdapter
from app.core.security import decrypt_secret
from app.models import ModelAccount, ModelProvider, VideoModel


class ConfiguredVideoModelAdapter(VideoModelAdapter):
    """Config-driven HTTP adapter used by real provider families.

    Provider APIs evolve independently. Endpoint paths and response field names live
    in ModelAccount.extra_config instead of being spread through business services.
    """

    provider_label = "Remote provider"

    def __init__(self, model: VideoModel) -> None:
        self.model = model
        self.account: ModelAccount = model.model_account
        self.provider: ModelProvider = self.account.provider
        self.base_url = (self.account.api_base_url or self.provider.default_api_base_url or "").rstrip("/")
        self.api_version = self.account.api_version or self.provider.default_api_version
        self.config = {
            **(self.provider.extra_config or {}),
            **(self.account.extra_config or {}),
            **(self.model.extra_config or {}),
        }
        self._last_payload: dict[str, dict[str, Any]] = {}

    def configuration_status(self) -> tuple[bool, str, dict[str, Any]]:
        missing: list[str] = []
        if not self.provider.enabled:
            missing.append("provider_enabled")
        if not self.account.enabled:
            missing.append("account_enabled")
        if not self.model.enabled:
            missing.append("model_enabled")
        if not self.base_url:
            missing.append("api_base_url")
        if not self.model.model_id:
            missing.append("model_id")
        auth_type = self.provider.auth_type
        if auth_type == "api_key" and not decrypt_secret(self.account.api_key_encrypted):
            missing.append("api_key")
        elif auth_type == "bearer_token" and not (
            decrypt_secret(self.account.api_key_encrypted)
            or decrypt_secret(self.account.access_token_encrypted)
        ):
            missing.append("api_key_or_access_token")
        elif auth_type == "oauth2" and not decrypt_secret(self.account.access_token_encrypted):
            missing.append("access_token")
        elif auth_type in {"google_adc", "service_account", "google_service_account"}:
            if not self.account.project_id:
                missing.append("project_id")
            if not self.account.region:
                missing.append("region")
            if auth_type in {"service_account", "google_service_account"} and not self.account.service_account_ref:
                missing.append("service_account_ref")
        paths = self.config.get("operation_paths", {})
        if not isinstance(paths, dict) or not paths.get("status"):
            missing.append("operation_paths.status")
        return (
            not missing,
            "真实 Adapter 配置完整；仍需使用官方凭证执行端到端验证" if not missing else "Adapter 配置不完整",
            {"provider": self.provider.code, "missing": missing},
        )

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        api_key = decrypt_secret(self.account.api_key_encrypted)
        access_token = decrypt_secret(self.account.access_token_encrypted)
        if api_key:
            header = str(self.config.get("api_key_header", "Authorization"))
            prefix = str(self.config.get("api_key_prefix", "Bearer "))
            headers[header] = f"{prefix}{api_key}"
        elif access_token:
            headers["Authorization"] = f"Bearer {access_token}"
        if self.api_version and self.config.get("api_version_header"):
            headers[str(self.config["api_version_header"])] = self.api_version
        return headers

    def _url(self, operation: str, provider_task_id: str | None = None) -> str:
        paths = self.config.get("operation_paths", {})
        path = paths.get(operation) if isinstance(paths, dict) else None
        if not path:
            raise RuntimeError(
                f"{self.provider_label} 缺少 operation_paths.{operation}；未调用未经配置的第三方接口"
            )
        rendered = str(path).format(
            task_id=provider_task_id or "",
            model_id=self.model.model_id or "",
            project_id=self.account.project_id or "",
            region=self.account.region or "",
        )
        return urljoin(f"{self.base_url}/", rendered.lstrip("/"))

    @staticmethod
    def _nested(payload: dict[str, Any], path: str, default: Any = None) -> Any:
        value: Any = payload
        for part in path.split("."):
            if not isinstance(value, dict) or part not in value:
                return default
            value = value[part]
        return value

    async def _submit(self, operation: str, request: GenerationRequest) -> str:
        configured, message, details = self.configuration_status()
        if not configured:
            raise RuntimeError(f"{message}: {', '.join(details['missing'])}")
        payload = {**(self.model.request_defaults or {})}
        fields = self.config.get("request_fields", {})
        if not isinstance(fields, dict):
            fields = {}
        payload[str(fields.get("model", "model"))] = self.model.model_id
        payload[str(fields.get("prompt", "prompt"))] = request.prompt
        for key, value in {
            str(fields.get("duration", "duration")): request.duration,
            str(fields.get("aspect_ratio", "aspect_ratio")): request.aspect_ratio,
            str(fields.get("resolution", "resolution")): request.resolution,
        }.items():
            if value is not None:
                payload[key] = value
        if request.source_image_path:
            payload[str(fields.get("image", "image"))] = base64.b64encode(
                request.source_image_path.read_bytes()
            ).decode("ascii")
        timeout = min(float(self.model.timeout_seconds), 60.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(self._url(operation), headers=self._headers(), json=payload)
            response.raise_for_status()
            data = response.json()
        task_field = str(self.config.get("task_id_field", "id"))
        task_id = self._nested(data, task_field)
        if not task_id:
            raise RuntimeError(f"{self.provider_label} 响应缺少任务 ID")
        self._last_payload[str(task_id)] = data
        return str(task_id)

    async def create_text_to_video(self, request: GenerationRequest) -> str:
        return await self._submit("text_to_video", request)

    async def create_image_to_video(self, request: GenerationRequest) -> str:
        if request.source_image_path is None:
            raise ValueError("图生视频缺少参考图片")
        return await self._submit("image_to_video", request)

    async def get_task_status(self, provider_task_id: str) -> str:
        async with httpx.AsyncClient(timeout=min(float(self.model.timeout_seconds), 60.0)) as client:
            response = await client.get(
                self._url("status", provider_task_id), headers=self._headers()
            )
            response.raise_for_status()
            data = response.json()
        self._last_payload[provider_task_id] = data
        status_field = str(self.config.get("status_field", "status"))
        raw = str(self._nested(data, status_field, "processing")).lower()
        statuses = self.config.get("status_mapping", {})
        if isinstance(statuses, dict):
            raw = str(statuses.get(raw, raw)).lower()
        return raw if raw in {"pending", "processing", "success", "failed"} else "processing"

    async def get_result(self, provider_task_id: str, work_dir: Path) -> GeneratedVideo:
        data = self._last_payload.get(provider_task_id, {})
        result_field = str(self.config.get("result_url_field", "output.url"))
        result_url = self._nested(data, result_field)
        if not result_url:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(
                    self._url("result", provider_task_id), headers=self._headers()
                )
                response.raise_for_status()
                data = response.json()
                result_url = self._nested(data, result_field)
        if not result_url:
            raise RuntimeError(f"{self.provider_label} 响应缺少视频结果 URL")
        target = work_dir / f"{provider_task_id}.mp4"
        async with httpx.AsyncClient(timeout=float(self.model.timeout_seconds)) as client:
            async with client.stream("GET", str(result_url), headers={"Accept": "video/*"}) as response:
                response.raise_for_status()
                with target.open("wb") as handle:
                    async for chunk in response.aiter_bytes():
                        handle.write(chunk)
        return GeneratedVideo(local_path=target, provider_task_id=provider_task_id)
