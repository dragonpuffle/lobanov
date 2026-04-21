import logging
import sys
from pathlib import Path
from typing import Any

from loguru import logger


def setup_logging(log_level: str = "INFO") -> None:
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )

    logger.remove()
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
    )

    logging.basicConfig(level=log_level, force=True)


def get_logger(name: str) -> Any:
    return logger.bind(name=name)
