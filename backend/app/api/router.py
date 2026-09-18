from fastapi import APIRouter

from app.api import auth, generation, logs, platforms, publishing, users, video_models, videos

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(video_models.public_router)
api_router.include_router(generation.router)
api_router.include_router(videos.router)
api_router.include_router(platforms.public_router)
api_router.include_router(publishing.router)
api_router.include_router(users.preferences_router)
api_router.include_router(users.router)
api_router.include_router(video_models.admin_router)
api_router.include_router(video_models.admin_provider_router)
api_router.include_router(video_models.admin_account_router)
api_router.include_router(platforms.admin_platform_router)
api_router.include_router(platforms.admin_account_router)
api_router.include_router(logs.router)
