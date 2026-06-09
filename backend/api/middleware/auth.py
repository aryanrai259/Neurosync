# Purpose:      FastAPI auth dependency — validates API keys on every protected request.
#               Reads the X-API-Key header, hashes it, looks up in api_keys table.
#               Returns the ApiKeyModel if valid; raises HTTP 401 / 403 otherwise.
#               Designed as a FastAPI Depends() — zero-cost on unprotected routes.
# Called By:    Any API endpoint that uses Depends(require_api_key) or
#               Depends(require_api_key_for_workspace)
# Calls:        core/auth.py (hash_api_key), db/repositories/api_key_repo.py
# Dependencies: fastapi, sqlalchemy
# Test File:    tests/unit/api/test_auth_middleware.py
#               tests/integration/api/test_auth_integration.py

import logging
from datetime import datetime, timezone

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.auth import hash_api_key
from backend.db.models.api_key import ApiKeyModel
from backend.db.repositories.api_key_repo import api_key_repo
from backend.db.session import get_db_session

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Sentinel header name
# ---------------------------------------------------------------------------

_HEADER_NAME = "X-API-Key"


# ---------------------------------------------------------------------------
# Core dependency
# ---------------------------------------------------------------------------

async def require_api_key(
    x_api_key: str | None = Header(default=None, alias=_HEADER_NAME),
    session: AsyncSession = Depends(get_db_session),
) -> ApiKeyModel:
    """
    FastAPI dependency — validates the X-API-Key header.

    Usage:
        @router.get("/protected")
        async def protected(key: ApiKeyModel = Depends(require_api_key)):
            ...

    Raises:
        HTTP 401 if no key provided.
        HTTP 401 if key hash not found or key is revoked.
        HTTP 403 if key is expired.

    Returns:
        The live ApiKeyModel for the authenticated key.
    """
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Provide X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    key_hash = hash_api_key(x_api_key)
    api_key = await api_key_repo.get_by_hash(session, key_hash)

    if api_key is None:
        logger.warning("Auth: rejected unknown or revoked key (hash prefix=%s)", key_hash[:8])
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked API key.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Check expiry
    if api_key.expires_at is not None:
        if api_key.expires_at < datetime.now(timezone.utc):
            logger.warning("Auth: rejected expired key id=%s", api_key.id)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="API key has expired.",
            )

    logger.debug("Auth: accepted key id=%s workspace=%s", api_key.id, api_key.workspace_id)
    return api_key


async def require_api_key_for_workspace(
    workspace_id_str: str,
    api_key: ApiKeyModel = Depends(require_api_key),
) -> ApiKeyModel:
    """
    Extension of require_api_key that additionally verifies the key belongs
    to the requested workspace.

    Usage: embed workspace_id from path into the dependency chain.

    Raises:
        HTTP 403 if the key's workspace_id does not match the requested workspace.
    """
    from uuid import UUID
    try:
        requested_ws = UUID(workspace_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid workspace_id format.",
        )

    if api_key.workspace_id != requested_ws:
        logger.warning(
            "Auth: workspace mismatch — key workspace=%s, requested=%s",
            api_key.workspace_id, requested_ws,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key does not belong to the requested workspace.",
        )
    return api_key


# ---------------------------------------------------------------------------
# Optional dependency (for endpoints that accept both authed and unauthed)
# ---------------------------------------------------------------------------

async def optional_api_key(
    x_api_key: str | None = Header(default=None, alias=_HEADER_NAME),
    session: AsyncSession = Depends(get_db_session),
) -> ApiKeyModel | None:
    """
    Like require_api_key but returns None if no key is provided.
    Useful for endpoints that have reduced functionality when unauthenticated.
    """
    if not x_api_key:
        return None
    try:
        return await require_api_key(x_api_key=x_api_key, session=session)
    except HTTPException:
        return None
