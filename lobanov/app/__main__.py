import uvicorn

from lobanov.compat.transformers_asr_no_torchcodec import disable_torchcodec_probe_for_asr
from lobanov.infra.config import GlobalConfig

if __name__ == "__main__":
    disable_torchcodec_probe_for_asr()
    config = GlobalConfig.load()
    uvicorn.run(
        app="lobanov.app.app:app",
        host="0.0.0.0",  # noqa: S104
        port=8000,
        reload=config.app.debug,
        log_level=config.app.log_level.lower(),
    )
