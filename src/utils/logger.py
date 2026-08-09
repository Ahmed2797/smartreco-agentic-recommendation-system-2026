"""Central logging configuration for SmartReco.

Import :func:`get_logger` from application modules instead of configuring the
root logger in each module.  The configuration is applied once per process.
"""
import logging
import os
import sys
from pathlib import Path


LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(filename)s:%(lineno)d | %(message)s"


def configure_logging() -> None:
    """Configure console and file logging once, without replacing host logging."""
    root_logger = logging.getLogger()
    if getattr(root_logger, "_smartreco_configured", False):
        return

    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_directory = Path(__file__).resolve().parents[2] / "logs"
    log_directory.mkdir(exist_ok=True)
    formatter = logging.Formatter(LOG_FORMAT)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    file_handler = logging.FileHandler(log_directory / "smartreco.log", encoding="utf-8")
    file_handler.setFormatter(formatter)

    root_logger.setLevel(log_level)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    root_logger._smartreco_configured = True  # type: ignore[attr-defined]

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(name: str):
    configure_logging()
    return logging.getLogger(name)


# Backwards-compatible export for modules that need the logging constants.
logging = logging
