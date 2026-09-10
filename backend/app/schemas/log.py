import uuid
from datetime import datetime

from pydantic import BaseModel

from app.core.enums import AuditResult


class AuditLogOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID | None = None
    username: str | None = None
    action: str
    resource_type: str
    resource_id: str | None = None
    result: AuditResult
    ip_address: str | None = None
    error_message: str | None = None
    created_at: datetime
