import uuid

from sqlalchemy.orm import Session

from app.core.enums import AuditResult
from app.models import AuditLog


def add_audit_log(
    db: Session,
    *,
    action: str,
    resource_type: str,
    result: AuditResult,
    user_id: uuid.UUID | None = None,
    resource_id: str | None = None,
    ip_address: str | None = None,
    message: str | None = None,
) -> AuditLog:
    log = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        result=result,
        ip_address=ip_address,
        message=message[:1000] if message else None,
    )
    db.add(log)
    return log
