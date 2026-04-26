import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

from loguru import logger

if TYPE_CHECKING:
    from loguru import Record


class _InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = str(record.levelno)

        loc = f"{record.module}:{record.funcName}:{record.lineno}"
        logger.bind(name=record.name, loc=loc).opt(exception=record.exc_info).log(level, record.getMessage())


def _loguru_loc_patcher(record: "Record") -> None:
    record["extra"].setdefault("loc", f"{record['function']}:{record['line']}")


def setup_logging(log_level: str = "INFO") -> None:
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{extra[name]}</cyan>:<cyan>{extra[loc]}</cyan> | "
        "<level>{message}</level>"
    )

    logger.remove()
    logger.configure(patcher=_loguru_loc_patcher)
    logger.add(
        sys.stdout,
        format=log_format,
        level=log_level,
        colorize=True,
        backtrace=True,
        diagnose=True,
    )

    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    logger.add(
        log_dir / "app.log",
        format=log_format,
        level=log_level,
        rotation="1 day",
        retention="30 days",
        compression="zip",
        backtrace=True,
        diagnose=True,
        enqueue=True,
    )

    logger.add(
        log_dir / "error.log",
        format=log_format,
        level="ERROR",
        rotation="1 day",
        retention="90 days",
        compression="zip",
        backtrace=True,
        diagnose=True,
        enqueue=True,
    )

    intercept = _InterceptHandler()
    logging.basicConfig(handlers=[intercept], level=log_level, force=True)
    for name in ("", "uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"):
        log = logging.getLogger(name)
        log.handlers = [intercept]
        log.setLevel(log_level)
        log.propagate = False

    for noisy in ("watchfiles", "watchfiles.main"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> Any:
    return logger.bind(name=name)
