from datetime import UTC, datetime

from fastapi import APIRouter, Request
from sqlalchemy import select

from app.core.enums import AuditResult
from app.core.exceptions import AppError
from app.core.permissions import CurrentUser, DbSession
from app.core.security import create_access_token, verify_password
from app.models import User
from app.schemas.auth import LoginRequest, LoginResponse
from app.schemas.common import SuccessResponse
from app.schemas.user import UserOut
from app.services.audit import add_audit_log

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=SuccessResponse[LoginResponse])
def login(payload: LoginRequest, request: Request, db: DbSession) -> SuccessResponse[LoginResponse]:
    user = db.scalar(select(User).where(User.username == payload.username))
    ip_address = request.client.host if request.client else None
    if user is None or not verify_password(payload.password, user.password_hash):
        add_audit_log(
            db,
            action="auth.login",
            resource_type="user",
            result=AuditResult.FAILED,
            ip_address=ip_address,
            message="Invalid credentials",
        )
        db.commit()
        raise AppError(401, "用户名或密码错误", "INVALID_CREDENTIALS")
    if not user.enabled:
        add_audit_log(
            db,
            user_id=user.id,
            action="auth.login",
            resource_type="user",
            resource_id=str(user.id),
            result=AuditResult.FAILED,
            ip_address=ip_address,
            message="Disabled account",
        )
        db.commit()
        raise AppError(401, "账号已停用", "ACCOUNT_DISABLED")
    user.last_login_at = datetime.now(UTC)
    add_audit_log(
        db,
        user_id=user.id,
        action="auth.login",
        resource_type="user",
        resource_id=str(user.id),
        result=AuditResult.SUCCESS,
        ip_address=ip_address,
    )
    db.commit()
    db.refresh(user)
    response = LoginResponse(
        access_token=create_access_token(str(user.id), user.role.value),
        user=UserOut.model_validate(user),
    )
    return SuccessResponse(data=response)


@router.get("/me", response_model=SuccessResponse[UserOut])
def me(user: CurrentUser) -> SuccessResponse[UserOut]:
    return SuccessResponse(data=UserOut.model_validate(user))
