"""Structured JSON logging with secret redaction.

Usage: log.info("event.name", extra={"source": "...", "count": 3})
Any environment value whose variable name ends in KEY/TOKEN/SECRET/PASSWORD is
scrubbed from every log line, so secrets from .env never reach the logs.
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

_SECRET_NAME = re.compile(r"(KEY|TOKEN|SECRET|PASSWORD)$", re.IGNORECASE)
_STD_ATTRS = set(
    logging.LogRecord("x", 0, "x", 0, "x", None, None).__dict__.keys()
) | {"message", "asctime", "taskName"}


def _secret_values() -> list[str]:
    vals = [v for k, v in os.environ.items() if _SECRET_NAME.search(k) and v and len(v) >= 6]
    return sorted(set(vals), key=len, reverse=True)


class JsonFormatter(logging.Formatter):
    def __init__(self) -> None:
        super().__init__()
        self._secrets = _secret_values()

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _STD_ATTRS and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        line = json.dumps(payload, default=str, ensure_ascii=False)
        for secret in self._secrets:
            line = line.replace(secret, "***")
        return line


def setup_logging(level: str = "INFO", log_file: Path | None = None) -> None:
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level.upper())
    formatter = JsonFormatter()

    stderr = logging.StreamHandler(sys.stderr)
    stderr.setFormatter(formatter)
    root.addHandler(stderr)

    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setFormatter(formatter)
        root.addHandler(fh)

    # httpx logs every request URL at INFO; keep that out of our logs.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
