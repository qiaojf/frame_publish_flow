import uuid

from fastapi import APIRouter, Query, Response, status

from app.core.permissions import AdminUser, DbSession
from app.schemas.common import PageResult, SuccessResponse
from app.schemas.user import PasswordReset, UserCreate, UserOut, UserUpdate
from app.services.users import UserService

router = APIRouter(prefix="/admin/users", tags=["Admin / Users"])


@router.get("", response_model=PageResult[UserOut])
def list_users(
    db: DbSession,
    _: AdminUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = None,
) -> PageResult[UserOut]:
    users, total = UserService.list(db, page=page, page_size=page_size, keyword=keyword)
    return PageResult(items=[UserOut.model_validate(user) for user in users], total=total, page=page, page_size=page_size)


@router.post("", response_model=SuccessResponse[UserOut], status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, db: DbSession, actor: AdminUser) -> SuccessResponse[UserOut]:
    return SuccessResponse(data=UserOut.model_validate(UserService.create(db, payload, actor)))


@router.patch("/{user_id}", response_model=SuccessResponse[UserOut])
def update_user(
    user_id: uuid.UUID,
    payload: UserUpdate,
    db: DbSession,
    actor: AdminUser,
) -> SuccessResponse[UserOut]:
    return SuccessResponse(data=UserOut.model_validate(UserService.update(db, user_id, payload, actor)))


@router.post("/{user_id}/reset-password", response_model=SuccessResponse[dict[str, bool]])
def reset_password(
    user_id: uuid.UUID,
    payload: PasswordReset,
    db: DbSession,
    actor: AdminUser,
) -> SuccessResponse[dict[str, bool]]:
    UserService.reset_password(db, user_id, payload, actor)
    return SuccessResponse(data={"reset": True})


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: uuid.UUID, db: DbSession, actor: AdminUser) -> Response:
    UserService.delete(db, user_id, actor)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
