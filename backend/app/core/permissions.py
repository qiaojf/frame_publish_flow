import uuid
from typing import Annotated

import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.enums import UserRole
from app.core.exceptions import AppError, ForbiddenError
from app.core.locale import resolve_locale
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models import User

bearer = HTTPBearer(auto_error=False)
DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    db: DbSession,
) -> User:
    if credentials is None:
        raise AppError(401, "请先登录", "NOT_AUTHENTICATED")
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = uuid.UUID(str(payload.get("sub")))
    except (jwt.PyJWTError, TypeError, ValueError) as exc:
        raise AppError(401, "登录凭证无效或已过期", "INVALID_TOKEN") from exc
    user = db.get(User, user_id)
    if user is None or not user.enabled:
        raise AppError(401, "账号不存在或已停用", "ACCOUNT_DISABLED")
    request.state.locale = resolve_locale(preferred_locale=user.preferred_locale)
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_admin(user: CurrentUser) -> User:
    if user.role != UserRole.ADMIN:
        raise ForbiddenError("仅管理员可以访问此功能", "ADMIN_REQUIRED")
    return user


AdminUser = Annotated[User, Depends(require_admin)]
