from contextlib import asynccontextmanager

from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from lobanov.app.api.v1 import (
    audio_router,
    auth_router,
    health_router,
    medical_documents_router,
    session_router,
    templates_router,
    transcription_router,
)
from lobanov.app.di import container
from lobanov.infra.config import GlobalConfig
from lobanov.utils.logging import get_logger, setup_logging

settings = GlobalConfig.load()
setup_logging(settings.app.log_level)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("Starting up application...")
    yield
    logger.info("Shutting down application...")
    await container.close()
    logger.info("Application shut down successfully")


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    error_message = f"Unhandled exception: {exc!s}"
    # Use a single "{}" arg so JSON or other "{" in the message is not parsed as Loguru format fields.
    logger.error("{}", error_message, exc_info=True, extra={"path": request.url.path})  # noqa: LOG014, PLE1205
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "message": "An unexpected error occurred. Please try again later.",
        },
    )


async def http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    if isinstance(exc, HTTPException):
        if exc.status_code >= status.HTTP_500_INTERNAL_SERVER_ERROR:
            logger.opt(exception=exc.__cause__).error(
                "HTTP exception: {code} - {detail!r} (path={path})",
                code=exc.status_code,
                detail=exc.detail,
                path=request.url.path,
            )
        else:
            logger.warning(
                "HTTP exception: {code} - {detail!r} (path={path})",
                code=exc.status_code,
                detail=exc.detail,
                path=request.url.path,
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

    setup_dishka(container=container, app=app)

    app.add_exception_handler(Exception, global_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)

    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(session_router, prefix="/api/v1")
    app.include_router(audio_router, prefix="/api/v1")
    app.include_router(transcription_router, prefix="/api/v1")
    app.include_router(templates_router, prefix="/api/v1")
    app.include_router(medical_documents_router, prefix="/api/v1")

    @app.get("/")
    async def root():
        return {"message": "Medical Documentation Assistant API", "status": "running"}

    return app


app = create_app()
