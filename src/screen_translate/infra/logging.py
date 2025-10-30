"""Logging utilities for Screen Translate."""

from __future__ import annotations

import logging
from typing import Optional

try:
    from loguru import logger as loguru_logger
except ImportError:  # pragma: no cover
    loguru_logger = None


def setup_logging(enable_loguru: bool = True, level: int = logging.INFO) -> None:
    """Configure application-wide logging.

    Args:
        enable_loguru: When True and loguru is available, bridge logging to loguru.
        level: Default logging level for stdlib logging.
    """
    logging.basicConfig(level=level, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    if enable_loguru and loguru_logger is not None:
        _bridge_standard_logging(loguru_logger)


def _bridge_standard_logging(logger: "loguru.Logger") -> None:
    """Redirect stdlib logging messages to loguru."""
    class LoguruHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            try:
                level = logger.level(record.levelname).name
            except ValueError:
                level = record.levelno
            logger.opt(depth=6, exception=record.exc_info).log(level, record.getMessage())

    logging.getLogger().handlers.clear()
    logging.getLogger().addHandler(LoguruHandler())
