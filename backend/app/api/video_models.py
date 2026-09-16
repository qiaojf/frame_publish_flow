import uuid
from urllib.parse import urlparse

from fastapi import APIRouter, Query, Response, status

from app.adapters.video_models import ModelAdapterFactory
from app.core.permissions import AdminUser, CurrentUser, DbSession
from app.core.security import decrypt_secret
from app.schemas.common import PageResult, SuccessResponse
from app.schemas.video_model import (
    AdapterTestResult,
    ModelAccountCreate,
    ModelAccountOut,
    ModelAccountUpdate,
    ModelProviderCreate,
    ModelProviderOut,
    ModelProviderUpdate,
    VideoModelCreate,
    VideoModelOut,
    VideoModelUpdate,
)
from app.services.catalog import CatalogService

public_router = APIRouter(prefix="/video-models", tags=["Video Models"])
admin_router = APIRouter(prefix="/admin/video-models", tags=["Admin / Video Models"])
admin_provider_router = APIRouter(prefix="/admin/model-providers", tags=["Admin / Model Providers"])
admin_account_router = APIRouter(prefix="/admin/model-accounts", tags=["Admin / Model Accounts"])


@admin_provider_router.get("", response_model=PageResult[ModelProviderOut])
def list_model_providers(
    db: DbSession,
    _: AdminUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = None,
) -> PageResult[ModelProviderOut]:
    providers, total = CatalogService.list_model_providers(
        db, page=page, page_size=page_size, keyword=keyword
    )
    return PageResult(
        items=[ModelProviderOut.from_model(provider) for provider in providers],
        total=total,
        page=page,
        page_size=page_size,
    )


@admin_provider_router.get("/{provider_id}", response_model=SuccessResponse[ModelProviderOut])
def get_model_provider(
    provider_id: uuid.UUID, db: DbSession, _: AdminUser
) -> SuccessResponse[ModelProviderOut]:
    return SuccessResponse(data=ModelProviderOut.from_model(CatalogService.get_model_provider(db, provider_id)))


@admin_provider_router.post(
    "", response_model=SuccessResponse[ModelProviderOut], status_code=status.HTTP_201_CREATED
)
def create_model_provider(
    payload: ModelProviderCreate, db: DbSession, actor: AdminUser
) -> SuccessResponse[ModelProviderOut]:
    provider = CatalogService.create_model_provider(db, payload, actor)
    return SuccessResponse(data=ModelProviderOut.from_model(provider))


@admin_provider_router.patch("/{provider_id}", response_model=SuccessResponse[ModelProviderOut])
def update_model_provider(
    provider_id: uuid.UUID,
    payload: ModelProviderUpdate,
    db: DbSession,
    actor: AdminUser,
) -> SuccessResponse[ModelProviderOut]:
    provider = CatalogService.update_model_provider(db, provider_id, payload, actor)
    return SuccessResponse(data=ModelProviderOut.from_model(provider))


@admin_provider_router.delete("/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_model_provider(provider_id: uuid.UUID, db: DbSession, actor: AdminUser) -> Response:
    CatalogService.delete_model_provider(db, provider_id, actor)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@admin_account_router.get("", response_model=PageResult[ModelAccountOut])
def list_model_accounts(
    db: DbSession,
    _: AdminUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = None,
    provider_id: uuid.UUID | None = None,
) -> PageResult[ModelAccountOut]:
    accounts, total = CatalogService.list_model_accounts(
        db,
        page=page,
        page_size=page_size,
        keyword=keyword,
        provider_id=provider_id,
    )
    return PageResult(
        items=[ModelAccountOut.from_model(account) for account in accounts],
        total=total,
        page=page,
        page_size=page_size,
    )


@admin_account_router.get("/{account_id}", response_model=SuccessResponse[ModelAccountOut])
def get_model_account(
    account_id: uuid.UUID, db: DbSession, _: AdminUser
) -> SuccessResponse[ModelAccountOut]:
    return SuccessResponse(data=ModelAccountOut.from_model(CatalogService.get_model_account(db, account_id)))


@admin_account_router.post(
    "", response_model=SuccessResponse[ModelAccountOut], status_code=status.HTTP_201_CREATED
)
def create_model_account(
    payload: ModelAccountCreate, db: DbSession, actor: AdminUser
) -> SuccessResponse[ModelAccountOut]:
    return SuccessResponse(
        data=ModelAccountOut.from_model(CatalogService.create_model_account(db, payload, actor))
    )


@admin_account_router.patch("/{account_id}", response_model=SuccessResponse[ModelAccountOut])
def update_model_account(
    account_id: uuid.UUID,
    payload: ModelAccountUpdate,
    db: DbSession,
    actor: AdminUser,
) -> SuccessResponse[ModelAccountOut]:
    return SuccessResponse(
        data=ModelAccountOut.from_model(
            CatalogService.update_model_account(db, account_id, payload, actor)
        )
    )


@admin_account_router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_model_account(account_id: uuid.UUID, db: DbSession, actor: AdminUser) -> Response:
    CatalogService.delete_model_account(db, account_id, actor)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@admin_account_router.post("/{account_id}/test", response_model=SuccessResponse[AdapterTestResult])
def test_model_account(
    account_id: uuid.UUID, db: DbSession, _: AdminUser
) -> SuccessResponse[AdapterTestResult]:
    account = CatalogService.get_model_account(db, account_id)
    provider = account.provider
    api_key_configured = bool(decrypt_secret(account.api_key_encrypted))
    access_token_configured = bool(decrypt_secret(account.access_token_encrypted))
    requirements = {
        "api_key": api_key_configured,
        "bearer_token": api_key_configured or access_token_configured,
        "google_adc": bool(account.project_id and account.region),
        "service_account": bool(account.project_id and account.region and account.service_account_ref),
        "google_service_account": bool(
            account.project_id and account.region and account.service_account_ref
        ),
        "oauth2": access_token_configured,
    }
    base_url = account.api_base_url or provider.default_api_base_url or ""
    parsed_url = urlparse(base_url)
    is_minimax = provider.adapter_family == "minimax"
    allowed_schemes = {"https"} if is_minimax else {"http", "https"}
    base_url_valid = bool(parsed_url.scheme in allowed_schemes and parsed_url.netloc)
    configured = (
        provider.enabled
        and account.enabled
        and requirements.get(provider.auth_type, True)
        and base_url_valid
    )
    return SuccessResponse(
        data=AdapterTestResult(
            configured=configured,
            adapter_type=provider.adapter_family,
            message=(
                "MiniMax configuration is complete. Real API verification has not been performed."
                if configured and is_minimax
                else "账号配置完整"
                if configured
                else "账号未启用、服务地址无效或认证配置不完整"
            ),
            details={
                "provider_code": provider.code,
                "auth_type": provider.auth_type,
                "credential_configured": requirements.get(provider.auth_type, True),
                "http_client_ready": base_url_valid,
                "real_api_verified": False,
            },
        )
    )


@public_router.get("", response_model=SuccessResponse[list[VideoModelOut]])
def list_public_models(db: DbSession, _: CurrentUser) -> SuccessResponse[list[VideoModelOut]]:
    models, _ = CatalogService.list_models(db, page=1, page_size=100, enabled_only=True)
    return SuccessResponse(data=[VideoModelOut.from_model(model) for model in models])


@admin_router.get("", response_model=PageResult[VideoModelOut])
def list_admin_models(
    db: DbSession,
    _: AdminUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = None,
) -> PageResult[VideoModelOut]:
    models, total = CatalogService.list_models(db, page=page, page_size=page_size, keyword=keyword)
    return PageResult(
        items=[VideoModelOut.from_model(model, admin=True) for model in models],
        total=total,
        page=page,
        page_size=page_size,
    )


@admin_router.get("/{model_id}", response_model=SuccessResponse[VideoModelOut])
def get_admin_model(model_id: uuid.UUID, db: DbSession, _: AdminUser) -> SuccessResponse[VideoModelOut]:
    return SuccessResponse(data=VideoModelOut.from_model(CatalogService.get_model(db, model_id), admin=True))


@admin_router.post("", response_model=SuccessResponse[VideoModelOut], status_code=status.HTTP_201_CREATED)
def create_model(
    payload: VideoModelCreate,
    db: DbSession,
    actor: AdminUser,
) -> SuccessResponse[VideoModelOut]:
    return SuccessResponse(data=VideoModelOut.from_model(CatalogService.create_model(db, payload, actor), admin=True))


@admin_router.patch("/{model_id}", response_model=SuccessResponse[VideoModelOut])
def update_model(
    model_id: uuid.UUID,
    payload: VideoModelUpdate,
    db: DbSession,
    actor: AdminUser,
) -> SuccessResponse[VideoModelOut]:
    return SuccessResponse(data=VideoModelOut.from_model(CatalogService.update_model(db, model_id, payload, actor), admin=True))


@admin_router.delete("/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_model(model_id: uuid.UUID, db: DbSession, actor: AdminUser) -> Response:
    CatalogService.delete_model(db, model_id, actor)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@admin_router.post("/{model_id}/test", response_model=SuccessResponse[AdapterTestResult])
def test_model(model_id: uuid.UUID, db: DbSession, _: AdminUser) -> SuccessResponse[AdapterTestResult]:
    model = CatalogService.get_model(db, model_id)
    adapter = ModelAdapterFactory.create(model)
    configured, message, details = adapter.configuration_status()
    if not (model.enabled and model.model_account.enabled and model.model_account.provider.enabled):
        configured = False
        message = "模型、模型账号或模型服务商已停用"
        details = {**details, "disabled": True}
    return SuccessResponse(
        data=AdapterTestResult(
            configured=configured,
            adapter_type=model.adapter_type,
            message=message,
            details=details,
        )
    )
