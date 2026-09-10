from fastapi import APIRouter, Query
from sqlalchemy import func, or_, select

from app.core.permissions import AdminUser, DbSession
from app.models import AuditLog, User
from app.schemas.common import PageResult
from app.schemas.log import AuditLogOut

router = APIRouter(prefix="/admin/logs", tags=["Admin / Audit Logs"])


@router.get("", response_model=PageResult[AuditLogOut])
def list_logs(
    db: DbSession,
    _: AdminUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = None,
    result: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> PageResult[AuditLogOut]:
    filters = []
    if result:
        filters.append(AuditLog.result == result)
    if date_from:
        filters.append(func.date(AuditLog.created_at) >= date_from)
    if date_to:
        filters.append(func.date(AuditLog.created_at) <= date_to)
    if keyword:
        pattern = f"%{keyword.strip()}%"
        filters.append(
            or_(
                User.username.ilike(pattern),
                AuditLog.action.ilike(pattern),
                AuditLog.resource_type.ilike(pattern),
            )
        )
    total = db.scalar(
        select(func.count())
        .select_from(AuditLog)
        .outerjoin(User, AuditLog.user_id == User.id)
        .where(*filters)
    ) or 0
    rows = db.execute(
        select(AuditLog, User.username)
        .outerjoin(User, AuditLog.user_id == User.id)
        .where(*filters)
        .order_by(AuditLog.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    items = [
        AuditLogOut(
            id=log.id,
            user_id=log.user_id,
            username=username,
            action=log.action,
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            result=log.result,
            ip_address=log.ip_address,
            error_message=log.message if log.result.value == "failed" else None,
            created_at=log.created_at,
        )
        for log, username in rows
    ]
    return PageResult(items=items, total=total, page=page, page_size=page_size)
