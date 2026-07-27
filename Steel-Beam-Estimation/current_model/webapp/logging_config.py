"""
Logging configuration — Phase D.2.

Logs application lifecycle and estimation events to current_model/logs/.
"""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from config.paths import LOGS_DIR, ensure_runtime_dirs


APP_LOGGER_NAME = "steel_beam"
ESTIMATION_LOGGER_NAME = "steel_beam.estimation"


def configure_logging(level: int = logging.INFO) -> logging.Logger:
    ensure_runtime_dirs()
    log_file = LOGS_DIR / "application.log"

    root = logging.getLogger()
    root.setLevel(level)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    # Avoid duplicate handlers on reload
    if not any(
        isinstance(h, RotatingFileHandler)
        and Path(getattr(h, "baseFilename", "")) == log_file
        for h in root.handlers
    ):
        fh = RotatingFileHandler(
            log_file,
            maxBytes=5 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        fh.setFormatter(formatter)
        fh.setLevel(level)
        root.addHandler(fh)

    if not any(isinstance(h, logging.StreamHandler) and not isinstance(h, RotatingFileHandler) for h in root.handlers):
        sh = logging.StreamHandler()
        sh.setFormatter(formatter)
        sh.setLevel(level)
        root.addHandler(sh)

    logger = logging.getLogger(APP_LOGGER_NAME)
    logger.info("Logging initialised — file=%s", log_file)
    return logger
