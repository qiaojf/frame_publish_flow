import uuid

from fastapi import APIRouter, Query, Request, Response, status
from fastapi.responses import FileResponse

from app.core.permissions import CurrentUser, DbSession
from app.schemas.common import PageResult, SuccessResponse
from app.schemas.video import VideoOut
from app.services.videos import VideoService

router = APIRouter(prefix="/videos", tags=["Videos"])


@router.get("", response_model=PageResult[VideoOut])
def list_videos(
    db: DbSession,
    user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = None,
    status_filter: str | None = Query(None, alias="status"),
) -> PageResult[VideoOut]:
    items, total = VideoService.list(
        db,
        user=user,
        page=page,
        page_size=page_size,
        keyword=keyword,
        status=status_filter,
    )
    return PageResult(items=items, total=total, page=page, page_size=page_size)


@router.get("/{video_id}", response_model=SuccessResponse[VideoOut])
def get_video(video_id: uuid.UUID, db: DbSession, user: CurrentUser) -> SuccessResponse[VideoOut]:
    return SuccessResponse(data=VideoService.get(db, video_id, user))


@router.get("/{video_id}/download")
def download_video(video_id: uuid.UUID, db: DbSession, user: CurrentUser) -> FileResponse:
    path, filename, media_type = VideoService.download_path(db, video_id, user)
    return FileResponse(path, filename=filename, media_type=media_type)


@router.delete("/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_video(video_id: uuid.UUID, request: Request, db: DbSession, user: CurrentUser) -> Response:
    VideoService.delete(db, video_id, user, request.client.host if request.client else None)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
