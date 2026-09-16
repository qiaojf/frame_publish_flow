import uuid

from fastapi import APIRouter, Query, Response, status
from sqlalchemy import select

from app.adapters.publishing import PublishAdapterFactory
from app.core.permissions import AdminUser, CurrentUser, DbSession
from app.models import PublishAccount
from app.schemas.common import PageResult, SuccessResponse
from app.schemas.platform import (
    PublishAccountCreate,
    PublishAccountOut,
    PublishAccountUpdate,
    PublishPlatformCreate,
    PublishPlatformOut,
    PublishPlatformUpdate,
)
from app.services.catalog import CatalogService
from app.schemas.video_model import AdapterTestResult

public_router = APIRouter(prefix="/publish/platforms", tags=["Publish Platforms"])
admin_platform_router = APIRouter(prefix="/admin/platforms", tags=["Admin / Publish Platforms"])
admin_account_router = APIRouter(prefix="/admin/accounts", tags=["Admin / Publish Accounts"])


@public_router.get("", response_model=SuccessResponse[list[PublishPlatformOut]])
def list_public_platforms(db: DbSession, _: CurrentUser) -> SuccessResponse[list[PublishPlatformOut]]:
    platforms, _ = CatalogService.list_platforms(db, page=1, page_size=100, enabled_only=True)
    items = []
    for platform in platforms:
        accounts = list(
            db.scalars(
                select(PublishAccount).where(
                    PublishAccount.platform_id == platform.id,
                    PublishAccount.enabled.is_(True),
                )
            )
        )
        items.append(PublishPlatformOut.from_model(platform, accounts=accounts))
    return SuccessResponse(data=items)


@admin_platform_router.get("", response_model=PageResult[PublishPlatformOut])
def list_admin_platforms(
    db: DbSession,
    _: AdminUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = None,
) -> PageResult[PublishPlatformOut]:
    platforms, total = CatalogService.list_platforms(db, page=page, page_size=page_size, keyword=keyword)
    items = []
    for platform in platforms:
        accounts = list(db.scalars(select(PublishAccount).where(PublishAccount.platform_id == platform.id)))
        item = PublishPlatformOut.from_model(platform, accounts=accounts, admin=True)
        items.append(item)
    return PageResult(items=items, total=total, page=page, page_size=page_size)


@admin_platform_router.get("/{platform_id}", response_model=SuccessResponse[PublishPlatformOut])
def get_admin_platform(
    platform_id: uuid.UUID,
    db: DbSession,
    _: AdminUser,
) -> SuccessResponse[PublishPlatformOut]:
    platform = CatalogService.get_platform(db, platform_id)
    accounts = list(db.scalars(select(PublishAccount).where(PublishAccount.platform_id == platform.id)))
    return SuccessResponse(data=PublishPlatformOut.from_model(platform, accounts=accounts, admin=True))


@admin_platform_router.post(
    "",
    response_model=SuccessResponse[PublishPlatformOut],
    status_code=status.HTTP_201_CREATED,
)
def create_platform(
    payload: PublishPlatformCreate,
    db: DbSession,
    actor: AdminUser,
) -> SuccessResponse[PublishPlatformOut]:
    return SuccessResponse(data=PublishPlatformOut.from_model(CatalogService.create_platform(db, payload, actor), admin=True))


@admin_platform_router.patch("/{platform_id}", response_model=SuccessResponse[PublishPlatformOut])
def update_platform(
    platform_id: uuid.UUID,
    payload: PublishPlatformUpdate,
    db: DbSession,
    actor: AdminUser,
) -> SuccessResponse[PublishPlatformOut]:
    return SuccessResponse(data=PublishPlatformOut.from_model(CatalogService.update_platform(db, platform_id, payload, actor), admin=True))


@admin_platform_router.delete("/{platform_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_platform(platform_id: uuid.UUID, db: DbSession, actor: AdminUser) -> Response:
    CatalogService.delete_platform(db, platform_id, actor)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@admin_account_router.get("", response_model=PageResult[PublishAccountOut])
def list_admin_accounts(
    db: DbSession,
    _: AdminUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = None,
    platform_id: uuid.UUID | None = None,
) -> PageResult[PublishAccountOut]:
    accounts, total = CatalogService.list_accounts(
        db,
        page=page,
        page_size=page_size,
        keyword=keyword,
        platform_id=platform_id,
    )
    return PageResult(
        items=[PublishAccountOut.from_model(account, admin=True) for account in accounts],
        total=total,
        page=page,
        page_size=page_size,
    )


@admin_account_router.post(
    "",
    response_model=SuccessResponse[PublishAccountOut],
    status_code=status.HTTP_201_CREATED,
)
def create_account(
    payload: PublishAccountCreate,
    db: DbSession,
    actor: AdminUser,
) -> SuccessResponse[PublishAccountOut]:
    return SuccessResponse(data=PublishAccountOut.from_model(CatalogService.create_account(db, payload, actor), admin=True))


@admin_account_router.patch("/{account_id}", response_model=SuccessResponse[PublishAccountOut])
def update_account(
    account_id: uuid.UUID,
    payload: PublishAccountUpdate,
    db: DbSession,
    actor: AdminUser,
) -> SuccessResponse[PublishAccountOut]:
    return SuccessResponse(data=PublishAccountOut.from_model(CatalogService.update_account(db, account_id, payload, actor), admin=True))


@admin_account_router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(account_id: uuid.UUID, db: DbSession, actor: AdminUser) -> Response:
    CatalogService.delete_account(db, account_id, actor)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@admin_account_router.post("/{account_id}/test", response_model=SuccessResponse[AdapterTestResult])
def test_account(
    account_id: uuid.UUID, db: DbSession, _: AdminUser
) -> SuccessResponse[AdapterTestResult]:
    account = CatalogService.get_account(db, account_id)
    platform = CatalogService.get_platform(db, account.platform_id)
    adapter = PublishAdapterFactory.create(platform, account)
    configured, message, details = adapter.configuration_status()
    if not (platform.enabled and account.enabled):
        configured = False
        message = "发布平台或账号已停用"
        details = {**details, "disabled": True}
    return SuccessResponse(
        data=AdapterTestResult(
            configured=configured,
            adapter_type=platform.adapter_type,
            message=message,
            details=details,
        )
    )
