"""Structured application logging."""

from __future__ import annotations

import logging
import sys
from typing import Any

from .config import settings

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
LOG_LEVEL = logging.DEBUG if settings.debug else logging.INFO


class JsonFormatter(logging.Formatter):
    """Minimal structured JSON log formatter for key events."""

    def format(self, record: logging.LogRecord) -> str:  # noqa: A003
        import json

        payload: dict[str, Any] = {
            "time": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        extra = getattr(record, "extra_fields", None)
        if isinstance(extra, dict):
            payload.update(extra)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging() -> None:
    root = logging.getLogger()
    if root.handlers:
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)
    root.setLevel(LOG_LEVEL)

    # Quiet noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


class JobLoggerAdapter(logging.LoggerAdapter):
    """Logger that injects job/video context into every emitted record."""

    def process(self, msg: str, kwargs: dict) -> tuple[str, dict]:  # noqa: D102
        extra = dict(kwargs.get("extra") or {})
        extra["extra_fields"] = {**self.extra, **extra.get("extra_fields", {})}
        kwargs["extra"] = extra
        return msg, kwargs


def job_logger(name: str, **context: Any) -> JobLoggerAdapter:
    return JobLoggerAdapter(logging.getLogger(name), context)
