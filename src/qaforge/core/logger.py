"""
qaforge.core.logger
===================
Dual logging strategy:
- `loguru` for human-readable, coloured console + structured file sinks.
- Python `logging` for compatibility with libraries (Playwright, requests,
  boto3) which all emit through the stdlib root logger.

We bridge the two via an `InterceptHandler` so a single configuration controls
everything.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

from loguru import logger as _logger

LOG_DIR = Path(__file__).resolve().parents[3] / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)


class InterceptHandler(logging.Handler):
    """Routes stdlib logging records into loguru."""

    def emit(self, record: logging.LogRecord) -> None:  # noqa: D401
        try:
            level = _logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back  # type: ignore[assignment]
            depth += 1
        _logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def configure_logging(level: str = "INFO") -> None:
    """Configure loguru sinks and intercept stdlib logging. Idempotent."""
    _logger.remove()
    _logger.add(
        sys.stdout,
        level=level,
        colorize=True,
        format="<green>{time:HH:mm:ss}</green> | <lvl>{level:<7}</lvl> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - {message}",
    )
    _logger.add(
        LOG_DIR / "qaforge.log",
        level="DEBUG",
        rotation="10 MB",
        retention="14 days",
        compression="zip",
        enqueue=True,
        backtrace=True,
        diagnose=False,  # diagnose=False to avoid leaking secrets
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:<7} | {name}:{function}:{line} - {message}",
    )
    # Bridge stdlib -> loguru
    logging.basicConfig(handlers=[InterceptHandler()], level=level, force=True)
    for noisy in ("urllib3", "asyncio", "websockets.client"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str = "qaforge"):
    """Return the loguru logger bound with a name."""
    return _logger.bind(name=name)
