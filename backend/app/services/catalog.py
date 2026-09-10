import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.enums import AuditResult
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.core.security import encrypt_secret
from app.models import PublishAccount, PublishPlatform, User, VideoModel
from app.schemas.platform import (
    PublishAccountCreate,
    PublishAccountUpdate,
    PublishPlatformCreate,
    PublishPlatformUpdate,
)
from app.schemas.video_model import VideoModelCreate, VideoModelUpdate
from app.services.audit import add_audit_log


def _commit_unique(db: Session, message: str, code: str) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError(message, code) from exc


class CatalogService:
    @staticmethod
    def list_models(
        db: Session,
        *,
        page: int,
        page_size: int,
        keyword: str | None = None,
        enabled_only: bool = False,
    ) -> tuple[list[VideoModel], int]:
        filters = [VideoModel.enabled.is_(True)] if enabled_only else []
        if keyword:
            pattern = f"%{keyword.strip()}%"
            filters.append(
                or_(
                    VideoModel.name.ilike(pattern),
                    VideoModel.code.ilike(pattern),
                    VideoModel.provider.ilike(pattern),
                )
            )
        total = db.scalar(select(func.count()).select_from(VideoModel).where(*filters)) or 0
        items = list(
            db.scalars(
                select(VideoModel)
                .where(*filters)
                .order_by(VideoModel.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        return items, total

    @staticmethod
    def get_model(db: Session, model_id: uuid.UUID) -> VideoModel:
        model = db.get(VideoModel, model_id)
        if model is None:
            raise NotFoundError("视频模型不存在", "MODEL_NOT_FOUND")
        return model

    @classmethod
    def create_model(cls, db: Session, payload: VideoModelCreate, actor: User) -> VideoModel:
        if not payload.supports_text_to_video and not payload.supports_image_to_video:
            raise ValidationError("至少启用一种生成能力", "MODEL_CAPABILITY_REQUIRED")
        values = payload.model_dump(exclude={"api_key"})
        model = VideoModel(
            id=uuid.uuid4(),
            **values,
            api_key_encrypted=encrypt_secret(payload.api_key),
        )
        db.add(model)
        add_audit_log(
            db,
            user_id=actor.id,
            action="video_model.create",
            resource_type="video_model",
            resource_id=str(model.id),
            result=AuditResult.SUCCESS,
        )
        _commit_unique(db, "模型编码已存在", "MODEL_CODE_EXISTS")
        db.refresh(model)
        return model

    @classmethod
    def update_model(
        cls,
        db: Session,
        model_id: uuid.UUID,
        payload: VideoModelUpdate,
        actor: User,
    ) -> VideoModel:
        model = cls.get_model(db, model_id)
        values = payload.model_dump(exclude_unset=True, exclude={"api_key"})
        for key, value in values.items():
            setattr(model, key, value)
        if payload.api_key:
            model.api_key_encrypted = encrypt_secret(payload.api_key)
        if not model.supports_text_to_video and not model.supports_image_to_video:
            raise ValidationError("至少启用一种生成能力", "MODEL_CAPABILITY_REQUIRED")
        add_audit_log(
            db,
            user_id=actor.id,
            action="video_model.update",
            resource_type="video_model",
            resource_id=str(model.id),
            result=AuditResult.SUCCESS,
        )
        _commit_unique(db, "模型编码已存在", "MODEL_CODE_EXISTS")
        db.refresh(model)
        return model

    @classmethod
    def delete_model(cls, db: Session, model_id: uuid.UUID, actor: User) -> None:
        model = cls.get_model(db, model_id)
        db.delete(model)
        add_audit_log(
            db,
            user_id=actor.id,
            action="video_model.delete",
            resource_type="video_model",
            resource_id=str(model_id),
            result=AuditResult.SUCCESS,
        )
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise ConflictError("模型已有生成任务，请改为停用", "MODEL_IN_USE") from exc

    @staticmethod
    def list_platforms(
        db: Session,
        *,
        page: int,
        page_size: int,
        keyword: str | None = None,
        enabled_only: bool = False,
    ) -> tuple[list[PublishPlatform], int]:
        filters = [PublishPlatform.enabled.is_(True)] if enabled_only else []
        if keyword:
            pattern = f"%{keyword.strip()}%"
            filters.append(or_(PublishPlatform.name.ilike(pattern), PublishPlatform.code.ilike(pattern)))
        total = db.scalar(select(func.count()).select_from(PublishPlatform).where(*filters)) or 0
        items = list(
            db.scalars(
                select(PublishPlatform)
                .where(*filters)
                .order_by(PublishPlatform.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        return items, total

    @staticmethod
    def get_platform(db: Session, platform_id: uuid.UUID) -> PublishPlatform:
        platform = db.get(PublishPlatform, platform_id)
        if platform is None:
            raise NotFoundError("发布平台不存在", "PLATFORM_NOT_FOUND")
        return platform

    @classmethod
    def create_platform(
        cls,
        db: Session,
        payload: PublishPlatformCreate,
        actor: User,
    ) -> PublishPlatform:
        platform = PublishPlatform(id=uuid.uuid4(), **payload.model_dump())
        db.add(platform)
        add_audit_log(
            db,
            user_id=actor.id,
            action="platform.create",
            resource_type="publish_platform",
            resource_id=str(platform.id),
            result=AuditResult.SUCCESS,
        )
        _commit_unique(db, "平台编码已存在", "PLATFORM_CODE_EXISTS")
        db.refresh(platform)
        return platform

    @classmethod
    def update_platform(
        cls,
        db: Session,
        platform_id: uuid.UUID,
        payload: PublishPlatformUpdate,
        actor: User,
    ) -> PublishPlatform:
        platform = cls.get_platform(db, platform_id)
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(platform, key, value)
        add_audit_log(
            db,
            user_id=actor.id,
            action="platform.update",
            resource_type="publish_platform",
            resource_id=str(platform.id),
            result=AuditResult.SUCCESS,
        )
        _commit_unique(db, "平台编码已存在", "PLATFORM_CODE_EXISTS")
        db.refresh(platform)
        return platform

    @classmethod
    def delete_platform(cls, db: Session, platform_id: uuid.UUID, actor: User) -> None:
        platform = cls.get_platform(db, platform_id)
        db.delete(platform)
        add_audit_log(
            db,
            user_id=actor.id,
            action="platform.delete",
            resource_type="publish_platform",
            resource_id=str(platform_id),
            result=AuditResult.SUCCESS,
        )
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise ConflictError("平台已有账号或发布任务，请改为停用", "PLATFORM_IN_USE") from exc

    @staticmethod
    def list_accounts(
        db: Session,
        *,
        page: int,
        page_size: int,
        keyword: str | None = None,
        platform_id: uuid.UUID | None = None,
        enabled_only: bool = False,
    ) -> tuple[list[PublishAccount], int]:
        filters = []
        if platform_id:
            filters.append(PublishAccount.platform_id == platform_id)
        if enabled_only:
            filters.append(PublishAccount.enabled.is_(True))
        if keyword:
            pattern = f"%{keyword.strip()}%"
            filters.append(
                or_(PublishAccount.name.ilike(pattern), PublishAccount.account_identifier.ilike(pattern))
            )
        total = db.scalar(select(func.count()).select_from(PublishAccount).where(*filters)) or 0
        items = list(
            db.scalars(
                select(PublishAccount)
                .where(*filters)
                .order_by(PublishAccount.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        return items, total

    @staticmethod
    def get_account(db: Session, account_id: uuid.UUID) -> PublishAccount:
        account = db.get(PublishAccount, account_id)
        if account is None:
            raise NotFoundError("发布账号不存在", "ACCOUNT_NOT_FOUND")
        return account

    @classmethod
    def create_account(
        cls,
        db: Session,
        payload: PublishAccountCreate,
        actor: User,
    ) -> PublishAccount:
        cls.get_platform(db, payload.platform_id)
        values = payload.model_dump(
            exclude={"client_id", "client_secret", "access_token", "refresh_token"}
        )
        account = PublishAccount(
            **values,
            client_id_encrypted=encrypt_secret(payload.client_id),
            client_secret_encrypted=encrypt_secret(payload.client_secret),
            access_token_encrypted=encrypt_secret(payload.access_token),
            refresh_token_encrypted=encrypt_secret(payload.refresh_token),
        )
        db.add(account)
        db.flush()
        add_audit_log(
            db,
            user_id=actor.id,
            action="publish_account.create",
            resource_type="publish_account",
            resource_id=str(account.id),
            result=AuditResult.SUCCESS,
        )
        db.commit()
        db.refresh(account)
        return account

    @classmethod
    def update_account(
        cls,
        db: Session,
        account_id: uuid.UUID,
        payload: PublishAccountUpdate,
        actor: User,
    ) -> PublishAccount:
        account = cls.get_account(db, account_id)
        if payload.platform_id:
            cls.get_platform(db, payload.platform_id)
        secret_map = {
            "client_id": "client_id_encrypted",
            "client_secret": "client_secret_encrypted",
            "access_token": "access_token_encrypted",
            "refresh_token": "refresh_token_encrypted",
        }
        values = payload.model_dump(exclude_unset=True, exclude=set(secret_map))
        for key, value in values.items():
            setattr(account, key, value)
        for input_name, column_name in secret_map.items():
            secret_value = getattr(payload, input_name)
            if secret_value:
                setattr(account, column_name, encrypt_secret(secret_value))
        add_audit_log(
            db,
            user_id=actor.id,
            action="publish_account.update",
            resource_type="publish_account",
            resource_id=str(account.id),
            result=AuditResult.SUCCESS,
        )
        db.commit()
        db.refresh(account)
        return account

    @classmethod
    def delete_account(cls, db: Session, account_id: uuid.UUID, actor: User) -> None:
        account = cls.get_account(db, account_id)
        db.delete(account)
        add_audit_log(
            db,
            user_id=actor.id,
            action="publish_account.delete",
            resource_type="publish_account",
            resource_id=str(account_id),
            result=AuditResult.SUCCESS,
        )
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise ConflictError("账号已有发布任务，请改为停用", "ACCOUNT_IN_USE") from exc
