import uuid

from fastapi import APIRouter, File, Form, Query, Request, UploadFile, status

from app.core.enums import GenerationStatus
from app.core.permissions import CurrentUser, DbSession
from app.schemas.common import PageResult, SuccessResponse
from app.schemas.generation import GenerationTaskOut
from app.services.generation import GenerationService
from app.models import VideoModel

router = APIRouter(prefix="/generation/tasks", tags=["Generation"])


@router.post("", response_model=SuccessResponse[GenerationTaskOut], status_code=status.HTTP_202_ACCEPTED)
def create_task(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    prompt: str = Form(""),
    model_id: uuid.UUID = Form(...),
    image: UploadFile | None = File(None),
    duration: int | None = Form(None),
    aspect_ratio: str | None = Form(None),
    resolution: str | None = Form(None),
) -> SuccessResponse[GenerationTaskOut]:
    task = GenerationService.create_task(
        db,
        user=user,
        prompt=prompt,
        model_id=model_id,
        image=image,
        duration=duration,
        aspect_ratio=aspect_ratio,
        resolution=resolution,
        ip_address=request.client.host if request.client else None,
    )
    model = db.get(VideoModel, task.model_id)
    return SuccessResponse(data=GenerationTaskOut.from_model(task, model.name if model else None))


@router.get("", response_model=PageResult[GenerationTaskOut])
def list_tasks(
    db: DbSession,
    user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: GenerationStatus | None = Query(None, alias="status"),
    keyword: str | None = None,
) -> PageResult[GenerationTaskOut]:
    rows, total = GenerationService.list_tasks(
        db,
        user=user,
        page=page,
        page_size=page_size,
        status=status_filter,
        keyword=keyword,
    )
    return PageResult(
        items=[GenerationTaskOut.from_model(task, model_name) for task, model_name in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{task_id}", response_model=SuccessResponse[GenerationTaskOut])
def get_task(task_id: uuid.UUID, db: DbSession, user: CurrentUser) -> SuccessResponse[GenerationTaskOut]:
    task, model_name = GenerationService.get_task(db, task_id, user)
    return SuccessResponse(data=GenerationTaskOut.from_model(task, model_name))
