import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.enums import AuditResult, PublishStatus, UserRole
from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.logging import logger
from app.models import PublishTask, User, Video, VideoGenerationTask, VideoModel
from app.schemas.video import VideoOut
from app.services.audit import add_audit_log
from app.storage import get_storage


class VideoService:
    @staticmethod
    def _publish_status(db: Session, video_id: uuid.UUID) -> str:
        statuses = list(db.scalars(select(PublishTask.status).where(PublishTask.video_id == video_id)))
        if not statuses:
            return "not_published"
        if any(status in {PublishStatus.PENDING, PublishStatus.PUBLISHING} for status in statuses):
            return "processing"
        if all(status == PublishStatus.SUCCESS for status in statuses):
            return "success"
        if any(status == PublishStatus.SUCCESS for status in statuses):
            return "partially_failed"
        return "failed"

    @classmethod
    def get_row(
        cls,
        db: Session,
        video_id: uuid.UUID,
        user: User,
    ) -> tuple[Video, VideoGenerationTask, VideoModel]:
        row = db.execute(
            select(Video, VideoGenerationTask, VideoModel)
            .join(VideoGenerationTask, Video.generation_task_id == VideoGenerationTask.id)
            .join(VideoModel, VideoGenerationTask.model_id == VideoModel.id)
            .where(Video.id == video_id, Video.is_deleted.is_(False))
        ).one_or_none()
        if row is None:
            raise NotFoundError("视频不存在或已删除", "VIDEO_NOT_FOUND")
        video, task, model = row
        if video.owner_id != user.id and user.role != UserRole.ADMIN:
            raise ForbiddenError("不能访问其他用户的视频")
        return video, task, model

    @classmethod
    def get(cls, db: Session, video_id: uuid.UUID, user: User) -> VideoOut:
        video, task, model = cls.get_row(db, video_id, user)
        return VideoOut.from_models(video, task, model.name, cls._publish_status(db, video.id))

    @classmethod
    def list(
        cls,
        db: Session,
        *,
        user: User,
        page: int,
        page_size: int,
        keyword: str | None = None,
        status: str | None = None,
    ) -> tuple[list[VideoOut], int]:
        filters = [Video.is_deleted.is_(False)]
        if user.role != UserRole.ADMIN:
            filters.append(Video.owner_id == user.id)
        if keyword:
            pattern = f"%{keyword.strip()}%"
            filters.append(or_(Video.title.ilike(pattern), Video.description.ilike(pattern), VideoGenerationTask.prompt.ilike(pattern)))
        if status:
            filters.append(VideoGenerationTask.status == status)
        base = (
            select(Video, VideoGenerationTask, VideoModel)
            .join(VideoGenerationTask, Video.generation_task_id == VideoGenerationTask.id)
            .join(VideoModel, VideoGenerationTask.model_id == VideoModel.id)
            .where(*filters)
        )
        total = db.scalar(
            select(func.count())
            .select_from(Video)
            .join(VideoGenerationTask, Video.generation_task_id == VideoGenerationTask.id)
            .where(*filters)
        ) or 0
        rows = list(
            db.execute(
                base.order_by(Video.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            ).all()
        )
        items = [
            VideoOut.from_models(video, task, model.name, cls._publish_status(db, video.id))
            for video, task, model in rows
        ]
        return items, total

    @classmethod
    def delete(cls, db: Session, video_id: uuid.UUID, user: User, ip_address: str | None = None) -> None:
        video, _, _ = cls.get_row(db, video_id, user)
        video.is_deleted = True
        video.deleted_at = datetime.now(UTC)
        add_audit_log(
            db,
            user_id=user.id,
            action="video.delete",
            resource_type="video",
            resource_id=str(video.id),
            result=AuditResult.SUCCESS,
            ip_address=ip_address,
        )
        db.commit()
        try:
            storage = get_storage()
            storage.delete(video.storage_key)
            storage.delete(video.thumbnail_storage_key)
        except Exception:
            logger.exception("video_storage_cleanup_failed", video_id=str(video.id), user_id=str(user.id))

    @classmethod
    def download_path(cls, db: Session, video_id: uuid.UUID, user: User) -> tuple[Path, str, str]:
        video, _, _ = cls.get_row(db, video_id, user)
        path = get_storage().resolve(video.storage_key)
        if not path.is_file():
            raise NotFoundError("视频文件不存在", "VIDEO_FILE_NOT_FOUND")
        filename = f"{video.title[:80] or 'video'}.mp4"
        return path, filename, video.mime_type
