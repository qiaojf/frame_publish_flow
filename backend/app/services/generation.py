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
from app.utils.images import read_image_dimensions

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
        account = model.model_account
        if not account.enabled:
            raise ValidationError("所选模型账号已停用", "MODEL_ACCOUNT_DISABLED")
        if not account.provider.enabled:
            raise ValidationError("所选模型服务商已停用", "MODEL_PROVIDER_DISABLED")
        capabilities = model.capabilities or {}
        if generation_type == GenerationType.TEXT_TO_VIDEO and not (
            model.supports_text_to_video and capabilities.get("text_to_video", True)
        ):
            raise ValidationError("所选模型不支持文生视频", "TEXT_TO_VIDEO_UNSUPPORTED")
        if generation_type == GenerationType.IMAGE_TO_VIDEO and not (
            model.supports_image_to_video and capabilities.get("image_to_video", True)
        ):
            raise ValidationError("所选模型不支持图生视频", "IMAGE_TO_VIDEO_UNSUPPORTED")
        duration_mode = capabilities.get("duration_mode")
        durations = capabilities.get("durations")
        if duration is not None:
            if duration_mode == "range":
                minimum = capabilities.get("duration_min")
                maximum = capabilities.get("duration_max")
                if (minimum is not None and duration < int(minimum)) or (
                    maximum is not None and duration > int(maximum)
                ):
                    raise ValidationError("视频时长不在当前模型允许范围内", "INVALID_DURATIONS")
            elif durations and duration not in durations:
                raise ValidationError("视频时长不在当前模型允许范围内", "INVALID_DURATIONS")
        aspect_key = (
            "aspect_ratios_image_to_video"
            if generation_type == GenerationType.IMAGE_TO_VIDEO
            else "aspect_ratios_text_to_video"
        )
        allowed_aspects = capabilities.get(aspect_key) or capabilities.get("aspect_ratios")
        if aspect_ratio is not None and allowed_aspects and aspect_ratio not in allowed_aspects:
            raise ValidationError("画面比例不在当前生成类型允许范围内", "INVALID_ASPECT_RATIOS")
        allowed_resolutions = capabilities.get("resolutions")
        if resolution is not None and allowed_resolutions and resolution not in allowed_resolutions:
            raise ValidationError("分辨率不在当前模型允许范围内", "INVALID_RESOLUTIONS")
        matrix = capabilities.get("resolution_duration_matrix")
        if isinstance(matrix, dict) and resolution and duration is not None:
            allowed_durations = matrix.get(resolution)
            if allowed_durations is not None and duration not in allowed_durations:
                raise ValidationError(
                    str(
                        capabilities.get(
                            "parameter_combination_error_message",
                            "当前分辨率与时长组合不受支持",
                        )
                    ),
                    str(
                        capabilities.get(
                            "parameter_combination_error_code",
                            "INVALID_RESOLUTION_DURATION",
                        )
                    ),
                )
        if generation_type == GenerationType.IMAGE_TO_VIDEO:
            max_images = int(capabilities.get("max_images", 1))
            if max_images < 1:
                raise ValidationError("当前模型不允许参考图片", "IMAGE_COUNT_EXCEEDED")

    @staticmethod
    def _save_image(
        image: UploadFile,
        *,
        max_size_mb: int | None = None,
        max_size_mb_exclusive: int | None = None,
    ) -> tuple[str, str]:
        settings = get_settings()
        suffix = Path(image.filename or "").suffix.lower()
        if image.content_type not in ALLOWED_IMAGE_MIME or suffix not in ALLOWED_IMAGE_SUFFIXES:
            raise ValidationError("参考图片仅支持 JPG、PNG 或 WebP", "INVALID_IMAGE_TYPE")
        normalized_suffix = ALLOWED_IMAGE_MIME[image.content_type]
        key = f"uploads/{uuid.uuid4().hex}{normalized_suffix}"
        try:
            image.file.seek(0)
            if max_size_mb_exclusive is not None:
                max_bytes = max_size_mb_exclusive * 1024 * 1024 - 1
                display_limit = f"小于 {max_size_mb_exclusive} MB"
            else:
                effective_mb = min(
                    settings.upload_max_size_mb,
                    max_size_mb or settings.upload_max_size_mb,
                )
                max_bytes = effective_mb * 1024 * 1024
                display_limit = f"不超过 {effective_mb} MB"
            get_storage().save_stream(image.file, key, max_bytes=max_bytes)
        except ValueError as exc:
            raise ValidationError(
                f"参考图片必须{display_limit}",
                "IMAGE_TOO_LARGE",
            ) from exc
        return key, get_storage().get_url(key)

    @staticmethod
    def _validate_image_dimensions(model: VideoModel, image_key: str) -> None:
        image_rules = (model.capabilities or {}).get("image")
        if not isinstance(image_rules, dict):
            return
        storage = get_storage()
        try:
            dimensions = read_image_dimensions(storage.resolve(image_key))
        except (OSError, ValueError) as exc:
            storage.delete(image_key)
            raise ValidationError("无法读取参考图片尺寸或图片内容无效", "INVALID_IMAGE_CONTENT") from exc
        short_edge = min(dimensions.width, dimensions.height)
        minimum = image_rules.get("short_edge_min_exclusive")
        if minimum is not None and short_edge <= int(minimum):
            storage.delete(image_key)
            raise ValidationError(
                f"参考图片短边必须大于 {int(minimum)} 像素",
                "IMAGE_DIMENSIONS_TOO_SMALL",
            )
        ratio = dimensions.width / dimensions.height
        minimum_ratio = image_rules.get("aspect_ratio_min")
        maximum_ratio = image_rules.get("aspect_ratio_max")
        if (minimum_ratio is not None and ratio < float(minimum_ratio)) or (
            maximum_ratio is not None and ratio > float(maximum_ratio)
        ):
            storage.delete(image_key)
            raise ValidationError(
                "参考图片宽高比必须在模型允许范围内",
                "INVALID_IMAGE_ASPECT_RATIO",
            )

    @classmethod
    def create_task(
        cls,
        db: Session,
        *,
        user: User,
        prompt: str | None,
        model_id: uuid.UUID,
        image: UploadFile | None,
        duration: int | None,
        aspect_ratio: str | None,
        resolution: str | None,
        ip_address: str | None = None,
    ) -> VideoGenerationTask:
        model = db.get(VideoModel, model_id)
        if model is None:
            raise NotFoundError("视频模型不存在", "MODEL_NOT_FOUND")
        generation_type = (
            GenerationType.IMAGE_TO_VIDEO if image is not None else GenerationType.TEXT_TO_VIDEO
        )
        normalized_prompt = (prompt or "").strip()
        prompt_rules = (model.capabilities or {}).get("prompt", {})
        if not isinstance(prompt_rules, dict):
            prompt_rules = {}
        prompt_required = bool(
            prompt_rules.get(
                "required_for_image_to_video"
                if generation_type == GenerationType.IMAGE_TO_VIDEO
                else "required_for_text_to_video",
                True,
            )
        )
        if prompt_required and not normalized_prompt:
            raise ValidationError("视频描述不能为空", "PROMPT_REQUIRED")
        defaults = model.request_defaults or {}
        if duration is None and defaults.get("duration") is not None:
            try:
                duration = int(defaults["duration"])
            except (TypeError, ValueError) as exc:
                raise ValidationError("模型默认时长配置无效", "MODEL_REQUEST_DEFAULT_INVALID") from exc
        aspect_ratio = aspect_ratio or (
            str(defaults["aspect_ratio"]) if defaults.get("aspect_ratio") else None
        )
        resolution = resolution or (
            str(defaults["resolution"]) if defaults.get("resolution") else None
        )
        max_prompt_length = prompt_rules.get("max_length") or model.capabilities.get(
            "max_prompt_length"
        )
        if max_prompt_length and len(normalized_prompt) > int(max_prompt_length):
            raise ValidationError("视频描述超过当前模型长度限制", "PROMPT_TOO_LONG")
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
            image_rules = model.capabilities.get("image", {})
            if not isinstance(image_rules, dict):
                image_rules = {}
            supported_formats = image_rules.get("formats") or model.capabilities.get(
                "supported_image_formats"
            )
            suffix = Path(image.filename or "").suffix.lower().lstrip(".")
            if supported_formats and suffix not in supported_formats:
                raise ValidationError("参考图片格式不受当前模型支持", "MODEL_IMAGE_FORMAT_UNSUPPORTED")
            image_key, image_url = cls._save_image(
                image,
                max_size_mb=model.capabilities.get("max_image_size_mb"),
                max_size_mb_exclusive=image_rules.get("max_size_mb_exclusive"),
            )
            cls._validate_image_dimensions(model, image_key)
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
