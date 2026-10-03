"""
Structured JSON logger for SchemaFlow.
Every log line includes run_id (if provided) so logs can be correlated.
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any


class JSONFormatter(logging.Formatter):
    """Emit log records as JSON lines."""

    def format(self, record: logging.LogRecord) -> str:  # type: ignore[override]
        payload: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        # Extra fields attached by get_logger() helpers
        for key in ("run_id", "node_id", "connector"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def _build_handler() -> logging.StreamHandler:  # type: ignore[type-arg]
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    return handler


def get_logger(name: str, **ctx: str) -> logging.LoggerAdapter:  # type: ignore[type-arg]
    """
    Return a logger that automatically injects extra context fields into
    every record.

    Usage::

        log = get_logger(__name__, run_id="abc-123")
        log.info("Fetching page", extra={"url": url})
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.addHandler(_build_handler())
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logging.LoggerAdapter(logger, extra=ctx)


# Root setup — called once at app startup
def configure_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    if not root.handlers:
        root.addHandler(_build_handler())
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
