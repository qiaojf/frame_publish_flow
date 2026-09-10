import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.logging import configure_logging, logger
from app.db.init_db import seed_database

settings = get_settings()
configure_logging()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    Path(settings.storage_path).mkdir(parents=True, exist_ok=True)
    if settings.auto_seed:
        seed_database()
    yield


app = FastAPI(
    title="FrameFlow API",
    version="0.1.0",
    description="AI 视频制作与多平台发布平台后端",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition", "X-Request-ID"],
)


@app.middleware("http")
async def request_context(request: Request, call_next):  # type: ignore[no-untyped-def]
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id)
    started = time.perf_counter()
    try:
        response = await call_next(request)
    finally:
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        logger.info("request_completed", method=request.method, path=request.url.path, elapsed_ms=elapsed_ms)
        structlog.contextvars.clear_contextvars()
    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(AppError)
async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "data": None, "message": exc.message, "error_code": exc.error_code},
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    error = exc.errors()[0] if exc.errors() else {}
    location = ".".join(str(item) for item in error.get("loc", [])[1:])
    detail = error.get("msg", "参数格式错误")
    message = f"{location}：{detail}" if location else str(detail)
    return JSONResponse(
        status_code=422,
        content={"success": False, "data": None, "message": message, "error_code": "REQUEST_VALIDATION_ERROR"},
    )


@app.exception_handler(HTTPException)
async def http_error_handler(_: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "data": None,
            "message": str(exc.detail),
            "error_code": f"HTTP_{exc.status_code}",
        },
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(_: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled_error", error_type=type(exc).__name__)
    return JSONResponse(
        status_code=500,
        content={"success": False, "data": None, "message": "服务内部错误", "error_code": "INTERNAL_ERROR"},
    )


@app.get("/health", tags=["System"])
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(api_router)
Path(settings.storage_path).mkdir(parents=True, exist_ok=True)
app.mount("/storage", StaticFiles(directory=settings.storage_path), name="storage")
