"""Unit tests for backend/api/middleware/auth.py

Tests the FastAPI dependency logic in isolation — mocks the DB session
so no live database is required. Tests 401/403 paths, expiry logic,
and the optional_api_key variant.
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi import HTTPException

from backend.api.middleware.auth import (
    require_api_key,
    require_api_key_for_workspace,
    optional_api_key,
)
from backend.db.models.api_key import ApiKeyModel


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_key_model(
    workspace_id=None,
    is_active=True,
    expires_at=None,
) -> ApiKeyModel:
    """Build a mock ApiKeyModel without hitting the DB."""
    key = MagicMock(spec=ApiKeyModel)
    key.id = uuid4()
    key.workspace_id = workspace_id or uuid4()
    key.key_hash = "abc123" * 10  # 60 chars — placeholder
    key.label = "test-key"
    key.is_active = is_active
    key.expires_at = expires_at
    key.last_used_at = None
    return key


# ---------------------------------------------------------------------------
# require_api_key — missing key
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_missing_api_key_raises_401():
    """No X-API-Key header → HTTP 401."""
    session = AsyncMock()
    with pytest.raises(HTTPException) as exc_info:
        await require_api_key(x_api_key=None, session=session)
    assert exc_info.value.status_code == 401
    assert "Missing" in exc_info.value.detail


# ---------------------------------------------------------------------------
# require_api_key — invalid / revoked key
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_invalid_api_key_raises_401():
    """Unknown key hash → HTTP 401."""
    session = AsyncMock()
    with patch(
        "backend.api.middleware.auth.api_key_repo.get_by_hash",
        new_callable=AsyncMock,
        return_value=None,
    ):
        with pytest.raises(HTTPException) as exc_info:
            await require_api_key(x_api_key="cb_invalid", session=session)
        assert exc_info.value.status_code == 401
        assert "Invalid" in exc_info.value.detail


# ---------------------------------------------------------------------------
# require_api_key — valid key
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_valid_api_key_returns_model():
    """Valid key → returns ApiKeyModel."""
    session = AsyncMock()
    mock_key = make_key_model()
    with patch(
        "backend.api.middleware.auth.api_key_repo.get_by_hash",
        new_callable=AsyncMock,
        return_value=mock_key,
    ):
        result = await require_api_key(x_api_key="cb_valid", session=session)
    assert result is mock_key


# ---------------------------------------------------------------------------
# require_api_key — expired key
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_expired_api_key_raises_403():
    """Expired key → HTTP 403."""
    session = AsyncMock()
    past = datetime.now(timezone.utc) - timedelta(days=1)
    mock_key = make_key_model(expires_at=past)
    with patch(
        "backend.api.middleware.auth.api_key_repo.get_by_hash",
        new_callable=AsyncMock,
        return_value=mock_key,
    ):
        with pytest.raises(HTTPException) as exc_info:
            await require_api_key(x_api_key="cb_expired", session=session)
        assert exc_info.value.status_code == 403
        assert "expired" in exc_info.value.detail.lower()


# ---------------------------------------------------------------------------
# require_api_key — non-expired key passes
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_future_expiry_key_passes():
    """Key with future expiry → allowed."""
    session = AsyncMock()
    future = datetime.now(timezone.utc) + timedelta(days=30)
    mock_key = make_key_model(expires_at=future)
    with patch(
        "backend.api.middleware.auth.api_key_repo.get_by_hash",
        new_callable=AsyncMock,
        return_value=mock_key,
    ):
        result = await require_api_key(x_api_key="cb_future", session=session)
    assert result is mock_key


# ---------------------------------------------------------------------------
# require_api_key_for_workspace — workspace match
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_workspace_scoped_key_correct_workspace():
    """Key workspace matches requested workspace → passes."""
    ws_id = uuid4()
    mock_key = make_key_model(workspace_id=ws_id)
    result = await require_api_key_for_workspace(
        workspace_id_str=str(ws_id),
        api_key=mock_key,
    )
    assert result is mock_key


# ---------------------------------------------------------------------------
# require_api_key_for_workspace — workspace mismatch
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_workspace_scoped_key_wrong_workspace_raises_403():
    """Key workspace != requested workspace → HTTP 403."""
    ws_id = uuid4()
    other_ws = uuid4()
    mock_key = make_key_model(workspace_id=other_ws)
    with pytest.raises(HTTPException) as exc_info:
        await require_api_key_for_workspace(
            workspace_id_str=str(ws_id),
            api_key=mock_key,
        )
    assert exc_info.value.status_code == 403
    assert "workspace" in exc_info.value.detail.lower()


# ---------------------------------------------------------------------------
# require_api_key_for_workspace — invalid UUID
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_workspace_scoped_invalid_uuid_raises_422():
    """Invalid UUID format → HTTP 422."""
    mock_key = make_key_model()
    with pytest.raises(HTTPException) as exc_info:
        await require_api_key_for_workspace(
            workspace_id_str="not-a-uuid",
            api_key=mock_key,
        )
    assert exc_info.value.status_code == 422


# ---------------------------------------------------------------------------
# optional_api_key
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_optional_api_key_no_header_returns_none():
    """No header → None (not an error)."""
    session = AsyncMock()
    result = await optional_api_key(x_api_key=None, session=session)
    assert result is None


@pytest.mark.asyncio
async def test_optional_api_key_invalid_returns_none():
    """Invalid key → None (not an error)."""
    session = AsyncMock()
    with patch(
        "backend.api.middleware.auth.api_key_repo.get_by_hash",
        new_callable=AsyncMock,
        return_value=None,
    ):
        result = await optional_api_key(x_api_key="cb_bad", session=session)
    assert result is None


@pytest.mark.asyncio
async def test_optional_api_key_valid_returns_model():
    """Valid key → returns ApiKeyModel."""
    session = AsyncMock()
    mock_key = make_key_model()
    with patch(
        "backend.api.middleware.auth.api_key_repo.get_by_hash",
        new_callable=AsyncMock,
        return_value=mock_key,
    ):
        result = await optional_api_key(x_api_key="cb_valid", session=session)
    assert result is mock_key
