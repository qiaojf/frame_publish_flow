import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.enums import AuditResult
from app.core.config import get_settings
from app.core.exceptions import ConflictError, NotFoundError
from app.core.security import hash_password
from app.models import User
from app.schemas.user import PasswordReset, UserCreate, UserPreferencesUpdate, UserUpdate
from app.services.audit import add_audit_log


class UserService:
    @staticmethod
    def list(db: Session, *, page: int, page_size: int, keyword: str | None) -> tuple[list[User], int]:
        filters = []
        if keyword:
            pattern = f"%{keyword.strip()}%"
            filters.append(or_(User.username.ilike(pattern), User.display_name.ilike(pattern), User.email.ilike(pattern)))
        total = db.scalar(select(func.count()).select_from(User).where(*filters)) or 0
        items = list(
            db.scalars(
                select(User)
                .where(*filters)
                .order_by(User.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        return items, total

    @staticmethod
    def create(db: Session, payload: UserCreate, actor: User) -> User:
        user = User(
            username=payload.username,
            display_name=payload.display_name,
            email=payload.email or None,
            password_hash=hash_password(payload.password),
            role=payload.role,
            enabled=payload.enabled,
            preferred_locale=payload.preferred_locale or get_settings().default_locale,
        )
        db.add(user)
        try:
            db.flush()
        except IntegrityError as exc:
            db.rollback()
            raise ConflictError("用户名或邮箱已存在", "USER_EXISTS") from exc
        add_audit_log(
            db,
            user_id=actor.id,
            action="user.create",
            resource_type="user",
            resource_id=str(user.id),
            result=AuditResult.SUCCESS,
        )
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def get(db: Session, user_id: uuid.UUID) -> User:
        user = db.get(User, user_id)
        if user is None:
            raise NotFoundError("用户不存在", "USER_NOT_FOUND")
        return user

    @staticmethod
    def update_preferences(db: Session, user: User, payload: UserPreferencesUpdate) -> User:
        user.preferred_locale = payload.preferred_locale
        add_audit_log(
            db,
            user_id=user.id,
            action="user.preferences.update",
            resource_type="user",
            resource_id=str(user.id),
            result=AuditResult.SUCCESS,
        )
        db.commit()
        db.refresh(user)
        return user

    @classmethod
    def update(cls, db: Session, user_id: uuid.UUID, payload: UserUpdate, actor: User) -> User:
        user = cls.get(db, user_id)
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(user, key, value)
        try:
            db.flush()
        except IntegrityError as exc:
            db.rollback()
            raise ConflictError("用户名或邮箱已存在", "USER_EXISTS") from exc
        add_audit_log(
            db,
            user_id=actor.id,
            action="user.update",
            resource_type="user",
            resource_id=str(user.id),
            result=AuditResult.SUCCESS,
        )
        db.commit()
        db.refresh(user)
        return user

    @classmethod
    def reset_password(cls, db: Session, user_id: uuid.UUID, payload: PasswordReset, actor: User) -> None:
        user = cls.get(db, user_id)
        user.password_hash = hash_password(payload.password)
        add_audit_log(
            db,
            user_id=actor.id,
            action="user.reset_password",
            resource_type="user",
            resource_id=str(user.id),
            result=AuditResult.SUCCESS,
        )
        db.commit()

    @classmethod
    def delete(cls, db: Session, user_id: uuid.UUID, actor: User) -> None:
        if user_id == actor.id:
            raise ConflictError("不能删除当前登录账号", "CANNOT_DELETE_SELF")
        user = cls.get(db, user_id)
        db.delete(user)
        add_audit_log(
            db,
            user_id=actor.id,
            action="user.delete",
            resource_type="user",
            resource_id=str(user_id),
            result=AuditResult.SUCCESS,
        )
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise ConflictError("用户已有业务数据，请改为停用账号", "USER_HAS_RESOURCES") from exc
