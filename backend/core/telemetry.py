# Purpose:      Structured telemetry for Company Brain backend.
#               Provides:
#                 - Structured JSON log formatter (replaces plain text in production)
#                 - RetrievalTrace schema (already in reasoning/schemas.py — reexported here)
#                 - RequestContext middleware helper
#                 - /api/v1/metrics endpoint (basic system metrics)
# Called By:    backend/main.py, backend/reasoning/pipeline.py
# Calls:        reasoning/schemas.py (RetrievalTrace)
# Dependencies: fastapi, logging, time, os
# Test File:    tests/unit/core/test_telemetry.py

import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any
from uuid import UUID


# ---------------------------------------------------------------------------
# Structured JSON log formatter
# ---------------------------------------------------------------------------

class StructuredFormatter(logging.Formatter):
    """
    Formats log records as JSON lines for machine parsing.

    Fields always present:
      ts       — ISO 8601 timestamp
      level    — levelname
      logger   — logger name
      msg      — the log message
      service  — "company-brain"

    Extra fields from `extra={}` dict are merged into the record.
    """

    SERVICE_NAME = "company-brain"

    def format(self, record: logging.LogRecord) -> str:
        log_dict: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "service": self.SERVICE_NAME,
        }

        # Merge extra fields (e.g. retrieval_trace, query_id)
        for key, value in record.__dict__.items():
            if key not in logging.LogRecord.__dict__ and not key.startswith("_"):
                try:
                    json.dumps(value)  # Test if serializable
                    log_dict[key] = value
                except (TypeError, ValueError):
                    log_dict[key] = str(value)

        # Include exception info if present
        if record.exc_info:
            log_dict["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(log_dict, default=str)


def configure_structured_logging(level: str = "INFO") -> None:
    """
    Replace the root logger's handlers with the structured JSON formatter.

    Call this in production startup. In test environments, plain text is
    preserved (pytest captures it better).
    """
    formatter = StructuredFormatter()
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    for handler in root_logger.handlers:
        handler.setFormatter(formatter)
    if not root_logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)


# ---------------------------------------------------------------------------
# Request timing helper — used in telemetry middleware
# ---------------------------------------------------------------------------

class RequestTimer:
    """Lightweight timer context manager."""

    def __init__(self) -> None:
        self._start: float = 0.0
        self.elapsed_ms: int = 0

    def __enter__(self) -> "RequestTimer":
        self._start = time.perf_counter()
        return self

    def __exit__(self, *_) -> None:
        self.elapsed_ms = int((time.perf_counter() - self._start) * 1000)


# ---------------------------------------------------------------------------
# System metrics collector
# ---------------------------------------------------------------------------

def collect_system_metrics() -> dict:
    """
    Collect lightweight process-level metrics without heavy dependencies.

    Returns a dict suitable for /api/v1/metrics response.
    """
    import sys
    import gc

    metrics: dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "service": "company-brain",
        "python_version": sys.version.split()[0],
    }

    # Memory — try psutil first, fall back to basic
    try:
        import psutil
        proc = psutil.Process(os.getpid())
        mem = proc.memory_info()
        metrics["memory"] = {
            "rss_mb": round(mem.rss / 1024 / 1024, 2),
            "vms_mb": round(mem.vms / 1024 / 1024, 2),
        }
        metrics["cpu_percent"] = proc.cpu_percent(interval=None)
    except ImportError:
        metrics["memory"] = {"note": "psutil not installed — install for memory metrics"}

    # GC stats
    metrics["gc"] = {
        f"gen{i}_collections": gc.get_count()[i] for i in range(3)
    }

    return metrics
