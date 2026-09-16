import uuid

from fastapi import APIRouter, File, Form, Header, Path, Query, Request, UploadFile, status
from pydantic import ValidationError as PydanticValidationError

from app.core.enums import PublishStatus
from app.core.exceptions import ValidationError
from app.core.permissions import CurrentUser, DbSession
from app.schemas.common import PageResult, SuccessResponse
from app.schemas.publishing import PublishBatchCreate, PublishBatchOut, PublishTaskOut
from app.services.publishing import PublishingService

router = APIRouter(prefix="/publish/tasks", tags=["Publishing"])


@router.post("", response_model=SuccessResponse[PublishBatchOut], status_code=status.HTTP_202_ACCEPTED)
def create_publish_tasks(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    payload: str = Form(...),
    cover: UploadFile | None = File(None),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", max_length=120),
) -> SuccessResponse[PublishBatchOut]:
    try:
        body = PublishBatchCreate.model_validate_json(payload)
    except PydanticValidationError as exc:
        first = exc.errors()[0]
        raise ValidationError(f"发布参数无效：{first.get('msg', '格式错误')}", "INVALID_PUBLISH_PAYLOAD") from exc
    tasks = PublishingService.create_batch(
        db,
        user=user,
        payload=body,
        idempotency_request_key=idempotency_key,
        cover=cover,
        ip_address=request.client.host if request.client else None,
    )
    return SuccessResponse(data=PublishBatchOut(tasks=[PublishingService.to_out(db, task) for task in tasks]))


@router.get("", response_model=PageResult[PublishTaskOut])
def list_publish_tasks(
    db: DbSession,
    user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = None,
    platform_id: uuid.UUID | None = None,
    video_id: uuid.UUID | None = None,
    status_filter: PublishStatus | None = Query(None, alias="status"),
    date_from: str | None = None,
    date_to: str | None = None,
) -> PageResult[PublishTaskOut]:
    items, total = PublishingService.list(
        db,
        user=user,
        page=page,
        page_size=page_size,
        keyword=keyword,
        platform_id=platform_id,
        video_id=video_id,
        status=status_filter,
        date_from=date_from,
        date_to=date_to,
    )
    return PageResult(items=items, total=total, page=page, page_size=page_size)


@router.get("/posts/{platform_post_id}", response_model=SuccessResponse[PublishTaskOut])
def get_published_post(
    db: DbSession,
    user: CurrentUser,
    platform_post_id: str = Path(min_length=1, max_length=255),
) -> SuccessResponse[PublishTaskOut]:
    return SuccessResponse(
        data=PublishingService.get_by_platform_post_id(db, platform_post_id, user)
    )


@router.get("/{task_id}", response_model=SuccessResponse[PublishTaskOut])
def get_publish_task(
    task_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
) -> SuccessResponse[PublishTaskOut]:
    task, _, _, _ = PublishingService.get_context(db, task_id, user)
    return SuccessResponse(data=PublishingService.to_out(db, task))


@router.post("/{task_id}/retry", response_model=SuccessResponse[PublishTaskOut], status_code=status.HTTP_202_ACCEPTED)
def retry_publish_task(
    task_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
) -> SuccessResponse[PublishTaskOut]:
    task = PublishingService.retry(db, task_id, user)
    return SuccessResponse(data=PublishingService.to_out(db, task))
