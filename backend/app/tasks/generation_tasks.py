import asyncio
import tempfile
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

from app.adapters.video_models import ModelAdapterFactory
from app.adapters.video_models.base import GenerationRequest
from app.core.config import get_settings
from app.core.enums import AuditResult, GenerationStatus, GenerationType
from app.core.logging import logger
from app.db.session import SessionLocal
from app.models import Video, VideoGenerationTask, VideoModel
from app.services.audit import add_audit_log
from app.storage import get_storage
from app.tasks.celery_app import celery_app
from app.utils.media import MediaProcessor


@celery_app.task(name="generation.run")
def run_generation_task(task_id: str) -> None:
    settings = get_settings()
    generated_key: str | None = None
    thumbnail_key: str | None = None
    task_uuid = uuid.UUID(task_id)
    with SessionLocal() as db:
        task = db.get(VideoGenerationTask, task_uuid)
        if task is None or task.status in {GenerationStatus.SUCCESS, GenerationStatus.CANCELLED}:
            return
        model = db.get(VideoModel, task.model_id)
        if model is None:
            task.status = GenerationStatus.FAILED
            task.error_code = "MODEL_NOT_FOUND"
            task.error_message = "视频模型不存在"
            db.commit()
            return
        try:
            task.status = GenerationStatus.PROCESSING
            task.started_at = datetime.now(UTC)
            db.commit()
            adapter = ModelAdapterFactory.create(model)
            storage = get_storage()
            source_image_path = (
                storage.resolve(task.source_image_storage_key)
                if task.source_image_storage_key
                else None
            )
            request = GenerationRequest(
                prompt=task.prompt,
                duration=task.duration,
                aspect_ratio=task.aspect_ratio,
                resolution=task.resolution,
                source_image_path=source_image_path,
            )
            if task.generation_type == GenerationType.IMAGE_TO_VIDEO:
                provider_id = asyncio.run(adapter.create_image_to_video(request))
            else:
                provider_id = asyncio.run(adapter.create_text_to_video(request))
            task.provider_task_id = provider_id
            db.commit()

            deadline = time.monotonic() + min(model.timeout_seconds, settings.generation_timeout)
            while True:
                provider_status = asyncio.run(adapter.get_task_status(provider_id))
                if provider_status in {"success", "failed"}:
                    break
                if time.monotonic() >= deadline:
                    task.status = GenerationStatus.TIMEOUT
                    task.error_code = "GENERATION_TIMEOUT"
                    task.error_message = "视频生成超时"
                    task.completed_at = datetime.now(UTC)
                    db.commit()
                    return
                time.sleep(max(1, settings.generation_poll_interval))
            if provider_status == "failed":
                raise RuntimeError("Mock 模型配置为模拟生成失败")

            with tempfile.TemporaryDirectory(prefix="frameflow-generation-") as work:
                work_dir = Path(work)
                generated = asyncio.run(adapter.get_result(provider_id, work_dir))
                media = MediaProcessor()
                metadata = media.probe(generated.local_path)
                thumb_path = media.thumbnail(generated.local_path, work_dir / "thumbnail.jpg")
                generated_key = f"videos/{task.user_id}/{task.id}.mp4"
                thumbnail_key = f"thumbnails/{task.user_id}/{task.id}.jpg"
                file_size = storage.save_file(generated.local_path, generated_key)
                storage.save_file(thumb_path, thumbnail_key)
                video = Video(
                    owner_id=task.user_id,
                    generation_task_id=task.id,
                    title=task.prompt[:80],
                    description=task.prompt,
                    video_url=storage.get_url(generated_key),
                    thumbnail_url=storage.get_url(thumbnail_key),
                    storage_key=generated_key,
                    thumbnail_storage_key=thumbnail_key,
                    file_size=file_size,
                    duration=metadata.duration,
                    width=metadata.width,
                    height=metadata.height,
                    mime_type=metadata.mime_type,
                )
                db.add(video)
                db.flush()
                task.result_video_id = video.id
                task.status = GenerationStatus.SUCCESS
                task.completed_at = datetime.now(UTC)
                add_audit_log(
                    db,
                    user_id=task.user_id,
                    action="generation.success",
                    resource_type="generation_task",
                    resource_id=str(task.id),
                    result=AuditResult.SUCCESS,
                )
                db.commit()
                logger.info(
                    "generation_succeeded",
                    task_id=str(task.id),
                    user_id=str(task.user_id),
                    provider=model.provider,
                    video_id=str(video.id),
                )
        except Exception as exc:
            db.rollback()
            task = db.get(VideoGenerationTask, task_uuid)
            if task is not None:
                task.status = GenerationStatus.FAILED
                task.error_code = "GENERATION_FAILED"
                task.error_message = str(exc)[:500] or "视频生成处理失败"
                task.completed_at = datetime.now(UTC)
                add_audit_log(
                    db,
                    user_id=task.user_id,
                    action="generation.failed",
                    resource_type="generation_task",
                    resource_id=str(task.id),
                    result=AuditResult.FAILED,
                    message=task.error_message,
                )
                db.commit()
            storage = get_storage()
            storage.delete(generated_key)
            storage.delete(thumbnail_key)
            logger.exception(
                "generation_failed",
                task_id=task_id,
                provider=model.provider,
            )
