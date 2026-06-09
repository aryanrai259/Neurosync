# Purpose:      Rate limiter configuration for Company Brain API.
#               Uses slowapi (Starlette middleware) with in-memory storage.
#               Limits are applied per-endpoint via the @limiter.limit() decorator.
#               Rate limit key = client IP (default) or API key ID when authenticated.
# Called By:    backend/main.py (limiter middleware setup)
#               Any endpoint using @limiter.limit()
# Calls:        slowapi.Limiter
# Dependencies: slowapi
# Test File:    tests/unit/api/test_rate_limiter.py

import logging

from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Per-endpoint rate limits (configurable constants)
# ---------------------------------------------------------------------------

# Ingestion endpoints — expensive ops, heavy limit
INGEST_RATE = "10/minute"

# Query / reasoning — LLM calls are expensive
QUERY_RATE = "20/minute"

# Standard read operations
READ_RATE = "60/minute"

# Auth endpoints — prevent brute-force
AUTH_RATE = "5/minute"

# Admin endpoints — destructive, tightly controlled
ADMIN_RATE = "5/minute"

# Health endpoints — monitoring tools poll frequently
HEALTH_RATE = "120/minute"


# ---------------------------------------------------------------------------
# Limiter instance — shared across all endpoints
# ---------------------------------------------------------------------------

def _get_rate_limit_key(request) -> str:
    """
    Rate limit key strategy:
    - If X-API-Key header is present, key on the API key (first 16 chars of hash).
    - Otherwise, fall back to client IP.

    This ensures API key holders share a limit across IPs, while unauthenticated
    clients are limited per-IP.
    """
    raw_key = request.headers.get("X-API-Key")
    if raw_key:
        import hashlib
        return "apikey:" + hashlib.sha256(raw_key.encode()).hexdigest()[:16]
    return get_remote_address(request)


limiter = Limiter(key_func=_get_rate_limit_key)
