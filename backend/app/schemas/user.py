import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import UserRole
from app.core.locale import SupportedLocale


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    display_name: str | None = None
    email: str | None = None
    role: UserRole
    enabled: bool
    preferred_locale: SupportedLocale
    last_login_at: datetime | None = None
    created_at: datetime


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=80, pattern=r"^[A-Za-z0-9_.-]+$")
    display_name: str | None = Field(default=None, max_length=120)
    email: str | None = Field(default=None, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    role: UserRole = UserRole.USER
    enabled: bool = True
    preferred_locale: SupportedLocale | None = None


class UserUpdate(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=80, pattern=r"^[A-Za-z0-9_.-]+$")
    display_name: str | None = Field(default=None, max_length=120)
    email: str | None = Field(default=None, max_length=255)
    role: UserRole | None = None
    enabled: bool | None = None


class PasswordReset(BaseModel):
    password: str = Field(min_length=8, max_length=128)


class UserPreferencesUpdate(BaseModel):
    preferred_locale: SupportedLocale
