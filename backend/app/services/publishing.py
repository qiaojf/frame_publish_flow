import hashlib
import json
import uuid

from fastapi import UploadFile
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.enums import AuditResult, PublishStatus, UserRole
from app.core.exceptions import AppError, ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.models import PublishAccount, PublishPlatform, PublishTask, User, Video
from app.schemas.publishing import PublishBatchCreate, PublishTaskOut
from app.services.audit import add_audit_log
from app.services.generation import GenerationService
from app.services.videos import VideoService


class PublishingService:
    @staticmethod
    def _task_key(
        request_key: str,
        user_id: uuid.UUID,
        platform_id: uuid.UUID,
        account_id: uuid.UUID,
    ) -> str:
        value = f"{user_id}:{request_key}:{platform_id}:{account_id}".encode()
        return hashlib.sha256(value).hexdigest()

    @staticmethod
    def _validate_platform_fields(
        platform: PublishPlatform,
        *,
        title: str,
        content: str | None,
        tags: list[str],
        overrides: dict[str, object],
        has_cover: bool,
    ) -> None:
        if platform.capabilities.get("supports_video") is False:
            raise ValidationError(f"{platform.name} 不支持视频发布", "PLATFORM_VIDEO_UNSUPPORTED")
        if has_cover and platform.capabilities.get("supports_cover") is False:
            raise ValidationError(f"{platform.name} 不支持自定义封面", "PLATFORM_COVER_UNSUPPORTED")
        common = {"title": title, "description": content, "content": content, "tags": tags}
        for field in platform.capabilities.get("fields", []):
            if isinstance(field, str):
                continue
            if not isinstance(field, dict) or not field.get("key"):
                continue
            key = str(field["key"])
            value = overrides.get(key, common.get(key))
            if field.get("required") and (value is None or value == "" or value == []):
                raise ValidationError(f"{platform.name} 缺少必填字段：{field.get('label', key)}", "PLATFORM_FIELD_REQUIRED")
            max_length = field.get("max_length")
            if max_length and isinstance(value, str) and len(value) > int(max_length):
                raise ValidationError(f"{platform.name} 的{field.get('label', key)}超过长度限制", "PLATFORM_FIELD_TOO_LONG")

    @classmethod
    def create_batch(
        cls,
        db: Session,
        *,
        user: User,
        payload: PublishBatchCreate,
        idempotency_request_key: str | None,
        cover: UploadFile | None = None,
        ip_address: str | None = None,
    ) -> list[PublishTask]:
        VideoService.get_row(db, payload.video_id, user)
        target_pairs = {(target.platform_id, target.account_id) for target in payload.targets}
        if len(target_pairs) != len(payload.targets):
            raise ValidationError("同一平台账号不能在一次请求中重复选择", "DUPLICATE_TARGET")
        request_key = idempotency_request_key or uuid.uuid4().hex
        keys = [
            cls._task_key(request_key, user.id, target.platform_id, target.account_id)
            for target in payload.targets
        ]
        existing = list(db.scalars(select(PublishTask).where(PublishTask.idempotency_key.in_(keys))))
        if existing:
            if len(existing) != len(keys):
                raise ConflictError("幂等请求存在不完整任务，请更换 Idempotency-Key", "IDEMPOTENCY_CONFLICT")
            by_key = {task.idempotency_key: task for task in existing}
            for target, key in zip(payload.targets, keys, strict=True):
                task = by_key[key]
                public_overrides = {
                    name: value
                    for name, value in task.platform_overrides.items()
                    if not name.startswith("_")
                }
                if (
                    task.user_id != user.id
                    or task.video_id != payload.video_id
                    or task.title != payload.title
                    or task.content != payload.description
                    or task.tags != payload.tags
                    or public_overrides != target.overrides
                ):
                    raise ConflictError(
                        "Idempotency-Key 已用于不同的发布内容",
                        "IDEMPOTENCY_PAYLOAD_CONFLICT",
                    )
            return [by_key[key] for key in keys]

        cover_key = None
        if cover is not None:
            cover_key, _ = GenerationService._save_image(cover)
        tasks: list[PublishTask] = []
        for target, key in zip(payload.targets, keys, strict=True):
            platform = db.get(PublishPlatform, target.platform_id)
            account = db.get(PublishAccount, target.account_id)
            if platform is None:
                raise NotFoundError("发布平台不存在", "PLATFORM_NOT_FOUND")
            if account is None:
                raise NotFoundError("发布账号不存在", "ACCOUNT_NOT_FOUND")
            if not platform.enabled:
                raise ValidationError(f"{platform.name} 已停用", "PLATFORM_DISABLED")
            if not account.enabled:
                raise ValidationError(f"{account.name} 已停用", "ACCOUNT_DISABLED")
            if account.platform_id != platform.id:
                raise ValidationError("发布账号不属于所选平台", "ACCOUNT_PLATFORM_MISMATCH")
            cls._validate_platform_fields(
                platform,
                title=payload.title,
                content=payload.description,
                tags=payload.tags,
                overrides=target.overrides,
                has_cover=cover is not None,
            )
            overrides = dict(target.overrides)
            if cover_key:
                overrides["_cover_storage_key"] = cover_key
            task = PublishTask(
                video_id=payload.video_id,
                user_id=user.id,
                platform_id=platform.id,
                account_id=account.id,
                status=PublishStatus.PENDING,
                title=payload.title,
                content=payload.description,
                tags=payload.tags,
                platform_overrides=overrides,
                idempotency_key=key,
            )
            db.add(task)
            tasks.append(task)
        db.flush()
        for task in tasks:
            add_audit_log(
                db,
                user_id=user.id,
                action="publish.create",
                resource_type="publish_task",
                resource_id=str(task.id),
                result=AuditResult.SUCCESS,
                ip_address=ip_address,
            )
        db.commit()
        for task in tasks:
            db.refresh(task)
            try:
                from app.tasks.publish_tasks import run_publish_task

                run_publish_task.delay(str(task.id))
            except Exception:
                task.status = PublishStatus.FAILED
                task.error_code = "QUEUE_UNAVAILABLE"
                task.error_message = "任务队列暂时不可用"
                add_audit_log(
                    db,
                    user_id=user.id,
                    action="publish.queue_failed",
                    resource_type="publish_task",
                    resource_id=str(task.id),
                    result=AuditResult.FAILED,
                    message="Celery queue unavailable",
                )
                db.commit()
        return tasks

    @staticmethod
    def get_context(
        db: Session,
        task_id: uuid.UUID,
        user: User,
    ) -> tuple[PublishTask, Video, PublishPlatform, PublishAccount]:
        row = db.execute(
            select(PublishTask, Video, PublishPlatform, PublishAccount)
            .join(Video, PublishTask.video_id == Video.id)
            .join(PublishPlatform, PublishTask.platform_id == PublishPlatform.id)
            .join(PublishAccount, PublishTask.account_id == PublishAccount.id)
            .where(PublishTask.id == task_id)
        ).one_or_none()
        if row is None:
            raise NotFoundError("发布任务不存在", "PUBLISH_TASK_NOT_FOUND")
        task, video, platform, account = row
        if task.user_id != user.id and user.role != UserRole.ADMIN:
            raise ForbiddenError("不能访问其他用户的发布任务")
        return task, video, platform, account

    @classmethod
    def to_out(cls, db: Session, task: PublishTask) -> PublishTaskOut:
        row = db.execute(
            select(Video, PublishPlatform, PublishAccount)
            .join(PublishTask, PublishTask.video_id == Video.id)
            .join(PublishPlatform, PublishTask.platform_id == PublishPlatform.id)
            .join(PublishAccount, PublishTask.account_id == PublishAccount.id)
            .where(PublishTask.id == task.id)
        ).one()
        video, platform, account = row
        return PublishTaskOut.from_model(
            task,
            video_title=video.title,
            video_thumbnail_url=video.thumbnail_url,
            platform_name=platform.name,
            account_name=account.name,
        )

    @classmethod
    def list(
        cls,
        db: Session,
        *,
        user: User,
        page: int,
        page_size: int,
        keyword: str | None = None,
        platform_id: uuid.UUID | None = None,
        video_id: uuid.UUID | None = None,
        status: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> tuple[list[PublishTaskOut], int]:
        filters = []
        if user.role != UserRole.ADMIN:
            filters.append(PublishTask.user_id == user.id)
        if platform_id:
            filters.append(PublishTask.platform_id == platform_id)
        if video_id:
            filters.append(PublishTask.video_id == video_id)
        if status:
            filters.append(PublishTask.status == status)
        if date_from:
            filters.append(func.date(PublishTask.created_at) >= date_from)
        if date_to:
            filters.append(func.date(PublishTask.created_at) <= date_to)
        if keyword:
            pattern = f"%{keyword.strip()}%"
            filters.append(
                or_(
                    Video.title.ilike(pattern),
                    PublishPlatform.name.ilike(pattern),
                    PublishAccount.name.ilike(pattern),
                )
            )
        joined = (
            select(PublishTask)
            .join(Video, PublishTask.video_id == Video.id)
            .join(PublishPlatform, PublishTask.platform_id == PublishPlatform.id)
            .join(PublishAccount, PublishTask.account_id == PublishAccount.id)
            .where(*filters)
        )
        total = db.scalar(
            select(func.count())
            .select_from(PublishTask)
            .join(Video, PublishTask.video_id == Video.id)
            .join(PublishPlatform, PublishTask.platform_id == PublishPlatform.id)
            .join(PublishAccount, PublishTask.account_id == PublishAccount.id)
            .where(*filters)
        ) or 0
        tasks = list(
            db.scalars(
                joined.order_by(PublishTask.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        return [cls.to_out(db, task) for task in tasks], total

    @classmethod
    def retry(cls, db: Session, task_id: uuid.UUID, user: User) -> PublishTask:
        task, _, _, _ = cls.get_context(db, task_id, user)
        if task.status != PublishStatus.FAILED:
            raise ConflictError("只有失败的发布任务可以重试", "PUBLISH_TASK_NOT_FAILED")
        task.status = PublishStatus.PENDING
        task.error_code = None
        task.error_message = None
        task.started_at = None
        task.completed_at = None
        task.retry_count += 1
        add_audit_log(
            db,
            user_id=user.id,
            action="publish.retry",
            resource_type="publish_task",
            resource_id=str(task.id),
            result=AuditResult.SUCCESS,
        )
        db.commit()
        db.refresh(task)
        try:
            from app.tasks.publish_tasks import run_publish_task

            run_publish_task.delay(str(task.id))
        except Exception as exc:
            task.status = PublishStatus.FAILED
            task.error_code = "QUEUE_UNAVAILABLE"
            task.error_message = "任务队列暂时不可用"
            db.commit()
            raise AppError(503, "任务队列暂时不可用，请检查 Redis 和 Celery Worker", "QUEUE_UNAVAILABLE") from exc
        return task
