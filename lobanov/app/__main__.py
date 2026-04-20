import uvicorn

from lobanov.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "lobanov.app.app:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
