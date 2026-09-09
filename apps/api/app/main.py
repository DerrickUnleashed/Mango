"""OrchardVision FastAPI application."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.core.database import init_models
from app.core.errors import (
    ApiError,
    api_error_handler,
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.core.logging import configure_logging, get_logger
from app.routers import (
    experiments_router,
    health_router,
    jobs_router,
    videos_router,
)

configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if settings.auto_create_tables:
        init_models()
        logger.info("Database tables ensured")
    logger.info(
        "%s v%s starting (%s)", settings.app_name, settings.app_version, settings.environment
    )
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Visibility-aware self-supervised identity learning for long-term "
        "fruit tracking and counting in mango orchards.",
        lifespan=lifespan,
        openapi_url="/api/openapi.json" if settings.environment != "production" else None,
        docs_url="/api/docs" if settings.environment != "production" else None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_exception_handler(ApiError, api_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    app.include_router(health_router, prefix="/api")
    app.include_router(videos_router, prefix="/api")
    app.include_router(jobs_router, prefix="/api")
    app.include_router(experiments_router, prefix="/api")

    @app.get("/")
    def root() -> JSONResponse:
        return JSONResponse(
            {
                "service": settings.app_name,
                "version": settings.app_version,
                "docs": "/api/docs",
            }
        )

    return app


app = create_app()
