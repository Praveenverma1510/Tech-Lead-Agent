"""
Centralized logging setup.

Why this exists: every module needs a logger, and we want consistent
formatting (timestamp, level, module name) plus a single place to change
log level / handlers (e.g. to add file logging or JSON logging later)
without touching every file in the project.
"""

from __future__ import annotations

import logging
import sys

from app.config.settings import get_settings

_CONFIGURED = False


def _configure_root_logger() -> None:
    """Attach a single stream handler with a readable format.

    Guarded by a module-level flag so repeated calls to `get_logger()`
    (e.g. from many modules at import time) don't attach duplicate handlers,
    which would otherwise cause every log line to print multiple times.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return

    settings = get_settings()
    handler = logging.StreamHandler(stream=sys.stdout)
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(settings.log_level)
    root.addHandler(handler)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a module-scoped logger, configuring the root logger on first use.

    Usage: `logger = get_logger(__name__)` at the top of any module.
    """
    _configure_root_logger()
    return logging.getLogger(name)
