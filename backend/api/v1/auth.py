# Purpose:      Auth API endpoints — API key management for workspaces.
#               Provides key generation, listing, and revocation.
#               Key generation returns the raw key ONCE — it is never stored.
# Called By:    backend/main.py (router)
# Calls:        db/repositories/api_key_repo.py, core/auth.py, api/middleware/auth.py
# Dependencies: fastapi, sqlalchemy
# Test File:    tests/integration/api/test_auth_api.py

import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.auth import generate_api_key
from backend.core.rate_limiter import limiter, AUTH_RATE, READ_RATE
from backend.db.models.api_key import ApiKeyModel
from backend.db.repositories.api_key_repo import api_key_repo
from backend.db.repositories.workspace_repo import workspace_repo
from backend.db.session import get_db_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class GenerateKeyRequest(BaseModel):
    workspace_id: UUID
    label: str = "default"
    expires_at: datetime | None = None


class GenerateKeyResponse(BaseModel):
    """
    Returned ONCE at key creation.
    raw_key is the full cb_xxxx key — it is not stored anywhere and cannot be recovered.
    """
    id: UUID
    workspace_id: UUID
    label: str
    raw_key: str           # Show to user ONCE — not stored
    created_at: datetime


class ApiKeyListItem(BaseModel):
    """Safe representation of a key — no raw_key, no hash."""
    id: UUID
    workspace_id: UUID
    label: str
    is_active: bool
    expires_at: datetime | None
    last_used_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class RevokeResponse(BaseModel):
    id: UUID
    revoked: bool


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/keys",
    status_code=status.HTTP_201_CREATED,
    response_model=GenerateKeyResponse,
    summary="Generate a new API key for a workspace",
    description=(
        "Creates a new API key. The raw_key is returned ONCE and is NOT stored. "
        "Save it securely — it cannot be recovered. "
        "Only the SHA-256 hash is persisted."
    ),
)
@limiter.limit(AUTH_RATE)
async def generate_key(
    request: Request,
    body: GenerateKeyRequest,
    session: AsyncSession = Depends(get_db_session),
) -> GenerateKeyResponse:
    """Generate a new API key for a workspace. Rate limited: 5/min."""
    ws = await workspace_repo.get_by_id(session, body.workspace_id)
    if ws is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace {body.workspace_id} not found.",
        )

    raw_key, key_hash = generate_api_key()

    api_key = await api_key_repo.create_key(
        session=session,
        workspace_id=body.workspace_id,
        key_hash=key_hash,
        label=body.label,
        expires_at=body.expires_at,
    )

    logger.info(
        "Auth: generated API key id=%s workspace=%s label=%s",
        api_key.id, api_key.workspace_id, api_key.label,
    )

    return GenerateKeyResponse(
        id=api_key.id,
        workspace_id=api_key.workspace_id,
        label=api_key.label,
        raw_key=raw_key,
        created_at=api_key.created_at,
    )


@router.get(
    "/keys/{workspace_id}",
    response_model=list[ApiKeyListItem],
    summary="List API keys for a workspace",
)
async def list_keys(
    workspace_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> list[ApiKeyListItem]:
    """Return all API keys for a workspace (active and revoked). Hashes are never returned."""
    keys = await api_key_repo.list_for_workspace(session, workspace_id)
    return [
        ApiKeyListItem(
            id=k.id,
            workspace_id=k.workspace_id,
            label=k.label,
            is_active=k.is_active,
            expires_at=k.expires_at,
            last_used_at=k.last_used_at,
            created_at=k.created_at,
        )
        for k in keys
    ]


@router.delete(
    "/keys/{key_id}",
    response_model=RevokeResponse,
    summary="Revoke an API key",
    description="Soft-deletes the key — sets is_active=False. The record is retained for audit.",
)
async def revoke_key(
    key_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> RevokeResponse:
    """Revoke an API key by its UUID."""
    revoked = await api_key_repo.revoke(session, key_id)
    if not revoked:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API key {key_id} not found.",
        )
    logger.info("Auth: revoked API key id=%s", key_id)
    return RevokeResponse(id=key_id, revoked=True)
