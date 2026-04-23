import os
from datetime import UTC, datetime

import aiofiles
from dishka import FromDishka
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from lobanov.protocols.services import FileStorageProtocol

router = APIRouter(prefix="/health", tags=["health"])


class HealthCheckResponse:
    def __init__(self, status: str, timestamp: str):
        self.status = status
        self.timestamp = timestamp


class DatabaseHealthResponse(HealthCheckResponse):
    def __init__(self, status: str, timestamp: str, database_status: str, latency_ms: float | None = None):
        super().__init__(status, timestamp)
        self.database_status = database_status
        self.latency_ms = latency_ms


class StorageHealthResponse(HealthCheckResponse):
    def __init__(self, status: str, timestamp: str, storage_status: str, storage_path: str | None = None):
        super().__init__(status, timestamp)
        self.storage_status = storage_status
        self.storage_path = storage_path


@router.get(
    "",
    summary="Basic health check",
    description="Returns the basic health status of the API service.",
)
async def health_check() -> dict[str, str]:
    return {
        "status": "healthy",
        "timestamp": datetime.now(tz=UTC).isoformat(),
    }


@router.get(
    "/db",
    summary="Database health check",
    description="Checks the connectivity and latency of the database connection.",
)
async def database_health_check(
    session_factory: FromDishka[type[AsyncSession]],
) -> dict[str, str | float]:
    start_time = datetime.now(tz=UTC)

    try:
        async with session_factory() as session:
            result = await session.execute(text("SELECT 1"))
            result.fetchone()

        end_time = datetime.now(tz=UTC)
        latency_ms = (end_time - start_time).total_seconds() * 1000

        return {
            "status": "healthy",
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "database_status": "connected",
            "latency_ms": round(latency_ms, 2),
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "unhealthy",
                "timestamp": datetime.now(tz=UTC).isoformat(),
                "database_status": "disconnected",
                "error": str(e),
            },
        ) from e


@router.get(
    "/storage",
    summary="Storage health check",
    description="Checks the availability and write permissions of the file storage service.",
    responses={
        status.HTTP_200_OK: {
            "description": "Storage is available and writable",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "timestamp": "2024-01-15T10:00:00Z",
                        "storage_status": "available",
                        "storage_path": "/path/to/storage",
                    }
                }
            },
        },
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "Storage is unavailable or read-only",
            "content": {
                "application/json": {
                    "example": {
                        "status": "unhealthy",
                        "timestamp": "2024-01-15T10:00:00Z",
                        "storage_status": "unavailable",
                        "error": "Storage path does not exist: /path/to/storage",
                    }
                }
            },
        },
    },
)
async def storage_health_check(
    storage_service: FromDishka[FileStorageProtocol],
) -> dict[str, str | None]:
    try:
        storage_path = None

        if hasattr(storage_service, "base_path"):
            storage_path = str(storage_service.base_path)

            if not await aiofiles.os.path.exists(storage_path):
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail={
                        "status": "unhealthy",
                        "timestamp": datetime.now(tz=UTC).isoformat(),
                        "storage_status": "unavailable",
                        "error": f"Storage path does not exist: {storage_path}",
                    },
                )

            if not os.access(storage_path, os.W_OK):
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail={
                        "status": "unhealthy",
                        "timestamp": datetime.now(tz=UTC).isoformat(),
                        "storage_status": "read_only",
                        "error": f"Storage path is not writable: {storage_path}",
                    },
                )

        return {
            "status": "healthy",
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "storage_status": "available",
            "storage_path": storage_path,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "unhealthy",
                "timestamp": datetime.now(tz=UTC).isoformat(),
                "storage_status": "unavailable",
                "error": str(e),
            },
        ) from e
