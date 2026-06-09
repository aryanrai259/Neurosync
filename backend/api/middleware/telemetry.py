# Purpose:      Request latency middleware — records every HTTP request's path,
#               status code, and latency into the in-process metrics store.
#               Implemented as a Starlette BaseHTTPMiddleware so it wraps ALL routes.
# Called By:    backend/main.py (app.add_middleware)
# Calls:        api/v1/metrics.py (record_request)
# Dependencies: starlette
# Test File:    tests/unit/core/test_telemetry.py

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from backend.api.v1.metrics import record_request

logger = logging.getLogger(__name__)


class RequestLatencyMiddleware(BaseHTTPMiddleware):
    """
    Records per-request metrics for every HTTP call.

    Captures:
      - Request path (normalized — no UUIDs in keys)
      - HTTP status code
      - Elapsed time in milliseconds

    Path normalization: UUID segments are replaced with {id} to group
    routes like /api/v1/workspaces/abc-123 and /api/v1/workspaces/def-456
    into a single /api/v1/workspaces/{id} bucket.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = int((time.perf_counter() - start) * 1000)

        path = self._normalize_path(request.url.path)
        record_request(path, response.status_code, elapsed_ms)

        # Attach latency header for debugging
        response.headers["X-Response-Time-Ms"] = str(elapsed_ms)

        logger.debug(
            "Request: %s %s -> %d (%dms)",
            request.method, path, response.status_code, elapsed_ms,
        )
        return response

    @staticmethod
    def _normalize_path(path: str) -> str:
        """
        Replace UUID-like segments with {id} to bucket per-route metrics.

        Example:
          /api/v1/workspaces/550e8400-e29b-41d4-a716-446655440000
          → /api/v1/workspaces/{id}
        """
        import re
        _UUID_RE = re.compile(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            re.IGNORECASE,
        )
        return _UUID_RE.sub("{id}", path)
