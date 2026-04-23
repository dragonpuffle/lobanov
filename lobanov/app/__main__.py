import uvicorn

from lobanov.app.app import app
from lobanov.infra.config import GlobalConfig

if __name__ == "__main__":
    config = GlobalConfig.load()
    uvicorn.run(
        app,
        host="0.0.0.0",  # noqa: S104
        port=8000,
        reload=config.app.debug,
        log_level=config.app.log_level.lower(),
    )
