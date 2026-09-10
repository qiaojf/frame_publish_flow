from pathlib import Path
from typing import Any

from app.adapters.video_models.base import GeneratedVideo, GenerationRequest, VideoModelAdapter
from app.utils.media import MediaProcessor


class MockVideoModelAdapter(VideoModelAdapter):
    def __init__(self, extra_config: dict[str, Any] | None = None) -> None:
        self.extra_config = extra_config or {}
        self.media = MediaProcessor()

    async def create_text_to_video(self, request: GenerationRequest) -> str:
        return self.new_provider_task_id()

    async def create_image_to_video(self, request: GenerationRequest) -> str:
        if request.source_image_path is None:
            raise ValueError("图生视频缺少参考图片")
        return self.new_provider_task_id()

    async def get_task_status(self, provider_task_id: str) -> str:
        return "failed" if self.extra_config.get("simulate_failure") else "success"

    async def get_result(self, provider_task_id: str, work_dir: Path) -> GeneratedVideo:
        duration = int(self.extra_config.get("mock_duration_seconds", 2))
        path = self.media.create_mock_video(work_dir / f"{provider_task_id}.mp4", duration)
        return GeneratedVideo(local_path=path, provider_task_id=provider_task_id)
