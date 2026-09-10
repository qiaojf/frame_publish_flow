import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.enums import AuditResult, GenerationStatus, GenerationType, UserRole
from app.core.exceptions import AppError, ForbiddenError, NotFoundError, ValidationError
from app.models import User, VideoGenerationTask, VideoModel
from app.services.audit import add_audit_log
from app.storage import get_storage

ALLOWED_IMAGE_MIME = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
ALLOWED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


class GenerationService:
    @staticmethod
    def _validate_capabilities(
        model: VideoModel,
        generation_type: GenerationType,
        *,
        duration: int | None,
        aspect_ratio: str | None,
        resolution: str | None,
    ) -> None:
        if not model.enabled:
            raise ValidationError("所选视频模型已停用", "MODEL_DISABLED")
        if generation_type == GenerationType.TEXT_TO_VIDEO and not model.supports_text_to_video:
            raise ValidationError("所选模型不支持文生视频", "TEXT_TO_VIDEO_UNSUPPORTED")
        if generation_type == GenerationType.IMAGE_TO_VIDEO and not model.supports_image_to_video:
            raise ValidationError("所选模型不支持图生视频", "IMAGE_TO_VIDEO_UNSUPPORTED")
        checks = {
            "durations": (duration, "视频时长"),
            "aspect_ratios": (aspect_ratio, "画面比例"),
            "resolutions": (resolution, "分辨率"),
        }
        for capability, (value, label) in checks.items():
            allowed = model.capabilities.get(capability)
            if value is not None and allowed and value not in allowed:
                raise ValidationError(f"{label}不在当前模型允许范围内", f"INVALID_{capability.upper()}")
        if generation_type == GenerationType.IMAGE_TO_VIDEO:
            max_images = int(model.capabilities.get("max_images", 1))
            if max_images < 1:
                raise ValidationError("当前模型不允许参考图片", "IMAGE_COUNT_EXCEEDED")

    @staticmethod
    def _save_image(image: UploadFile) -> tuple[str, str]:
        settings = get_settings()
        suffix = Path(image.filename or "").suffix.lower()
        if image.content_type not in ALLOWED_IMAGE_MIME or suffix not in ALLOWED_IMAGE_SUFFIXES:
            raise ValidationError("参考图片仅支持 JPG、PNG 或 WebP", "INVALID_IMAGE_TYPE")
        normalized_suffix = ALLOWED_IMAGE_MIME[image.content_type]
        key = f"uploads/{uuid.uuid4().hex}{normalized_suffix}"
        try:
            image.file.seek(0)
            get_storage().save_stream(image.file, key, max_bytes=settings.upload_max_bytes)
        except ValueError as exc:
            raise ValidationError(
                f"参考图片不能超过 {settings.upload_max_size_mb} MB",
                "IMAGE_TOO_LARGE",
            ) from exc
        return key, get_storage().get_url(key)

    @classmethod
    def create_task(
        cls,
        db: Session,
        *,
        user: User,
        prompt: str,
        model_id: uuid.UUID,
        image: UploadFile | None,
        duration: int | None,
        aspect_ratio: str | None,
        resolution: str | None,
        ip_address: str | None = None,
    ) -> VideoGenerationTask:
        normalized_prompt = prompt.strip()
        if not normalized_prompt:
            raise ValidationError("视频描述不能为空", "PROMPT_REQUIRED")
        model = db.get(VideoModel, model_id)
        if model is None:
            raise NotFoundError("视频模型不存在", "MODEL_NOT_FOUND")
        generation_type = (
            GenerationType.IMAGE_TO_VIDEO if image is not None else GenerationType.TEXT_TO_VIDEO
        )
        cls._validate_capabilities(
            model,
            generation_type,
            duration=duration,
            aspect_ratio=aspect_ratio,
            resolution=resolution,
        )
        image_key = None
        image_url = None
        if image is not None:
            image_key, image_url = cls._save_image(image)
        task = VideoGenerationTask(
            user_id=user.id,
            model_id=model.id,
            generation_type=generation_type,
            prompt=normalized_prompt,
            source_image_storage_key=image_key,
            source_image_url=image_url,
            duration=duration,
            aspect_ratio=aspect_ratio,
            resolution=resolution,
            status=GenerationStatus.PENDING,
        )
        db.add(task)
        db.flush()
        add_audit_log(
            db,
            user_id=user.id,
            action="generation.create",
            resource_type="generation_task",
            resource_id=str(task.id),
            result=AuditResult.SUCCESS,
            ip_address=ip_address,
        )
        db.commit()
        db.refresh(task)
        try:
            from app.tasks.generation_tasks import run_generation_task

            run_generation_task.delay(str(task.id))
        except Exception as exc:
            task.status = GenerationStatus.FAILED
            task.error_code = "QUEUE_UNAVAILABLE"
            task.error_message = "任务队列暂时不可用"
            add_audit_log(
                db,
                user_id=user.id,
                action="generation.queue_failed",
                resource_type="generation_task",
                resource_id=str(task.id),
                result=AuditResult.FAILED,
                message="Celery queue unavailable",
            )
            db.commit()
            raise AppError(503, "任务队列暂时不可用，请检查 Redis 和 Celery Worker", "QUEUE_UNAVAILABLE") from exc
        return task

    @staticmethod
    def get_task(db: Session, task_id: uuid.UUID, user: User) -> tuple[VideoGenerationTask, str]:
        row = db.execute(
            select(VideoGenerationTask, VideoModel.name)
            .join(VideoModel, VideoGenerationTask.model_id == VideoModel.id)
            .where(VideoGenerationTask.id == task_id)
        ).one_or_none()
        if row is None:
            raise NotFoundError("生成任务不存在", "GENERATION_TASK_NOT_FOUND")
        task, model_name = row
        if task.user_id != user.id and user.role != UserRole.ADMIN:
            raise ForbiddenError("不能查看其他用户的生成任务")
        return task, model_name

    @staticmethod
    def list_tasks(
        db: Session,
        *,
        user: User,
        page: int,
        page_size: int,
        status: GenerationStatus | None = None,
        keyword: str | None = None,
    ) -> tuple[list[tuple[VideoGenerationTask, str]], int]:
        filters = []
        if user.role != UserRole.ADMIN:
            filters.append(VideoGenerationTask.user_id == user.id)
        if status:
            filters.append(VideoGenerationTask.status == status)
        if keyword:
            filters.append(VideoGenerationTask.prompt.ilike(f"%{keyword.strip()}%"))
        total = db.scalar(select(func.count()).select_from(VideoGenerationTask).where(*filters)) or 0
        rows = list(
            db.execute(
                select(VideoGenerationTask, VideoModel.name)
                .join(VideoModel, VideoGenerationTask.model_id == VideoModel.id)
                .where(*filters)
                .order_by(VideoGenerationTask.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            ).all()
        )
        return rows, total
