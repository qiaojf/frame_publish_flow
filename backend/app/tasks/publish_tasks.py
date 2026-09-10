import asyncio
import uuid
from datetime import UTC, datetime

from app.adapters.publishing import PublishAdapterFactory
from app.adapters.publishing.base import PermanentPublishError, PublishRequest, TemporaryPublishError
from app.core.config import get_settings
from app.core.enums import AuditResult, PublishStatus
from app.core.logging import logger
from app.db.session import SessionLocal
from app.models import PublishAccount, PublishPlatform, PublishTask, Video
from app.services.audit import add_audit_log
from app.storage import get_storage
from app.tasks.celery_app import celery_app


def _mark_failed(task_id: uuid.UUID, error_code: str, message: str) -> None:
    with SessionLocal() as db:
        task = db.get(PublishTask, task_id)
        if task is None:
            return
        task.status = PublishStatus.FAILED
        task.error_code = error_code
        task.error_message = message[:500]
        task.completed_at = datetime.now(UTC)
        add_audit_log(
            db,
            user_id=task.user_id,
            action="publish.failed",
            resource_type="publish_task",
            resource_id=str(task.id),
            result=AuditResult.FAILED,
            message=task.error_message,
        )
        db.commit()


@celery_app.task(bind=True, name="publish.run")
def run_publish_task(self, task_id: str) -> None:  # type: ignore[no-untyped-def]
    settings = get_settings()
    task_uuid = uuid.UUID(task_id)
    try:
        with SessionLocal() as db:
            task = db.get(PublishTask, task_uuid)
            if task is None or task.status in {PublishStatus.SUCCESS, PublishStatus.CANCELLED}:
                return
            video = db.get(Video, task.video_id)
            platform = db.get(PublishPlatform, task.platform_id)
            account = db.get(PublishAccount, task.account_id)
            if video is None or video.is_deleted:
                raise PermanentPublishError("视频不存在或已删除")
            if platform is None or account is None:
                raise PermanentPublishError("发布平台或账号不存在")
            task.status = PublishStatus.PUBLISHING
            task.started_at = datetime.now(UTC)
            db.commit()
            adapter = PublishAdapterFactory.create(platform, account)
            request = PublishRequest(
                video_path=get_storage().resolve(video.storage_key),
                title=task.title,
                content=task.content,
                tags=task.tags,
                overrides=task.platform_overrides,
                idempotency_key=task.idempotency_key,
            )
            result = asyncio.run(adapter.publish_video(request))
            task.platform_post_id = result.platform_post_id
            task.platform_post_url = result.platform_post_url
            if result.status == "processing":
                task.status = PublishStatus.PUBLISHING
                db.commit()
                return
            task.status = PublishStatus.SUCCESS
            task.completed_at = datetime.now(UTC)
            task.error_code = None
            task.error_message = None
            add_audit_log(
                db,
                user_id=task.user_id,
                action="publish.success",
                resource_type="publish_task",
                resource_id=str(task.id),
                result=AuditResult.SUCCESS,
            )
            db.commit()
            logger.info(
                "publish_succeeded",
                task_id=str(task.id),
                user_id=str(task.user_id),
                provider=platform.code,
            )
    except TemporaryPublishError as exc:
        if self.request.retries < settings.celery_max_retries:
            with SessionLocal() as db:
                task = db.get(PublishTask, task_uuid)
                if task:
                    task.status = PublishStatus.PENDING
                    task.retry_count += 1
                    db.commit()
            raise self.retry(exc=exc, countdown=min(60, 2 ** (self.request.retries + 1)))
        _mark_failed(task_uuid, "TEMPORARY_ERROR", "平台暂时不可用，自动重试次数已用尽")
    except PermanentPublishError as exc:
        _mark_failed(task_uuid, "PUBLISH_REJECTED", str(exc))
    except Exception:
        _mark_failed(task_uuid, "PUBLISH_FAILED", "发布处理失败，请检查平台配置")
        logger.exception("publish_failed", task_id=task_id)
