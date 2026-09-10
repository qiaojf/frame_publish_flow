import uuid

from fastapi import APIRouter, Query, Response, status

from app.core.permissions import AdminUser, CurrentUser, DbSession
from app.schemas.common import PageResult, SuccessResponse
from app.schemas.video_model import VideoModelCreate, VideoModelOut, VideoModelUpdate
from app.services.catalog import CatalogService

public_router = APIRouter(prefix="/video-models", tags=["Video Models"])
admin_router = APIRouter(prefix="/admin/video-models", tags=["Admin / Video Models"])


@public_router.get("", response_model=SuccessResponse[list[VideoModelOut]])
def list_public_models(db: DbSession, _: CurrentUser) -> SuccessResponse[list[VideoModelOut]]:
    models, _ = CatalogService.list_models(db, page=1, page_size=100, enabled_only=True)
    return SuccessResponse(data=[VideoModelOut.from_model(model) for model in models])


@admin_router.get("", response_model=PageResult[VideoModelOut])
def list_admin_models(
    db: DbSession,
    _: AdminUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = None,
) -> PageResult[VideoModelOut]:
    models, total = CatalogService.list_models(db, page=page, page_size=page_size, keyword=keyword)
    return PageResult(
        items=[VideoModelOut.from_model(model, admin=True) for model in models],
        total=total,
        page=page,
        page_size=page_size,
    )


@admin_router.get("/{model_id}", response_model=SuccessResponse[VideoModelOut])
def get_admin_model(model_id: uuid.UUID, db: DbSession, _: AdminUser) -> SuccessResponse[VideoModelOut]:
    return SuccessResponse(data=VideoModelOut.from_model(CatalogService.get_model(db, model_id), admin=True))


@admin_router.post("", response_model=SuccessResponse[VideoModelOut], status_code=status.HTTP_201_CREATED)
def create_model(
    payload: VideoModelCreate,
    db: DbSession,
    actor: AdminUser,
) -> SuccessResponse[VideoModelOut]:
    return SuccessResponse(data=VideoModelOut.from_model(CatalogService.create_model(db, payload, actor), admin=True))


@admin_router.patch("/{model_id}", response_model=SuccessResponse[VideoModelOut])
def update_model(
    model_id: uuid.UUID,
    payload: VideoModelUpdate,
    db: DbSession,
    actor: AdminUser,
) -> SuccessResponse[VideoModelOut]:
    return SuccessResponse(data=VideoModelOut.from_model(CatalogService.update_model(db, model_id, payload, actor), admin=True))


@admin_router.delete("/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_model(model_id: uuid.UUID, db: DbSession, actor: AdminUser) -> Response:
    CatalogService.delete_model(db, model_id, actor)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
