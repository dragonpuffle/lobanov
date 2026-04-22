from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from lobanov.app.api.v1 import (
    audio_router,
    health_router,
    medical_documents_router,
    session_router,
    templates_router,
)
from lobanov.infra.config import GlobalConfig
from lobanov.utils.logging import get_logger, setup_logging

settings = GlobalConfig.load()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up application...")
    setup_logging()
    logger.info("Application started successfully")
    yield
    logger.info("Shutting down application...")
    logger.info("Application shut down successfully")


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(f"Unhandled exception: {exc}", exc_info=True, extra={"path": request.url.path})
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "message": "An unexpected error occurred. Please try again later.",
        },
    )


async def http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    if isinstance(exc, HTTPException):
        logger.warning(
            f"HTTP exception: {exc.status_code} - {exc.detail}",
            extra={"path": request.url.path, "status_code": exc.status_code},
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app.name,
        description="Medical Documentation Assistant Backend API",
        version="0.1.0",
        docs_url="/docs" if settings.app.debug else None,
        redoc_url="/redoc" if settings.app.debug else None,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors.origins,
        allow_credentials=settings.cors.allow_credentials,
        allow_methods=settings.cors.allow_methods,
        allow_headers=settings.cors.allow_headers,
    )

    app.add_exception_handler(Exception, global_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)

    app.include_router(health_router, prefix="/api/v1")
    app.include_router(session_router, prefix="/api/v1")
    app.include_router(audio_router, prefix="/api/v1")
    app.include_router(templates_router, prefix="/api/v1")
    app.include_router(medical_documents_router, prefix="/api/v1")

    @app.get("/")
    async def root():
        return {"message": "Medical Documentation Assistant API", "status": "running"}

    return app


app = create_app()
