# Purpose:      API key authentication — generates, validates, and manages API keys.
#               Keys are workspace-scoped, stored hashed in PostgreSQL.
#               This is the MVP authentication layer — supports header-based key auth.
#               Future: upgrade to JWT / OIDC for multi-user production deployments.
# Called By:    backend/api/middleware/auth.py (FastAPI dependency)
# Calls:        db/repositories/api_key_repo.py
# Dependencies: hashlib, secrets, fastapi
# Test File:    tests/unit/core/test_auth.py

import hashlib
import secrets
import logging

logger = logging.getLogger(__name__)

# Key prefix for easy identification in logs
_API_KEY_PREFIX = "cb_"
_KEY_BYTES = 32  # 256-bit random key


def generate_api_key() -> tuple[str, str]:
    """
    Generate a new API key.

    Returns:
        (raw_key, key_hash) — raw_key is shown to the user ONCE,
        key_hash is stored in the database.
    """
    raw = _API_KEY_PREFIX + secrets.token_urlsafe(_KEY_BYTES)
    key_hash = _hash_key(raw)
    return raw, key_hash


def hash_api_key(raw_key: str) -> str:
    """Hash an incoming API key for comparison against stored hashes."""
    return _hash_key(raw_key)


def _hash_key(raw_key: str) -> str:
    """SHA-256 hash of the raw key. Deterministic for lookup."""
    return hashlib.sha256(raw_key.encode()).hexdigest()
