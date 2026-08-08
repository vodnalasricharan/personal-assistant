from __future__ import annotations

import json
import logging
from typing import Any

from config.settings import Settings


class JsonFormatter(logging.Formatter):
    """Format log records as JSON."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        extra = getattr(record, "extra_data", None)
        if isinstance(extra, dict):
            payload.update(extra)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(settings: Settings) -> None:
    """Configure application logging once."""

    root_logger = logging.getLogger()
    if any(isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler) for handler in root_logger.handlers):
        return

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())

    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
