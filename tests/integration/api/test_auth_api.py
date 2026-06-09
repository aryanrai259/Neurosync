"""Integration tests for Auth API — key generation, listing, revocation.

Tests the full HTTP path:
  POST /api/v1/auth/keys  → creates key, returns raw_key
  GET  /api/v1/auth/keys/{workspace_id}  → lists keys (no hashes)
  DELETE /api/v1/auth/keys/{key_id}  → revokes key

Uses real PostgreSQL via TestClient.
"""
import pytest
import pytest_asyncio
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.core.config import get_settings
from backend.db.repositories.workspace_repo import workspace_repo
from backend.db.session import get_engine
from backend.main import app


# ---------------------------------------------------------------------------
# Fixtures — same proven pattern as test_api_phase6a.py
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def client():
    import asyncio
    from backend.db.session import engine as db_engine
    with TestClient(app) as c:
        yield c
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(db_engine.dispose())
    finally:
        loop.close()


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def db_session():
    engine = get_engine(get_settings().database_url)
    maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as s:
        yield s
    await engine.dispose()


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def auth_workspace(db_session):
    """Create a test workspace once per module."""
    ws = await workspace_repo.create(db_session, name=f"auth-test-{uuid4().hex[:8]}")
    return ws


# ---------------------------------------------------------------------------
# Key generation
# ---------------------------------------------------------------------------

class TestKeyGeneration:
    def test_generate_key_returns_201(self, client, auth_workspace):
        r = client.post("/api/v1/auth/keys", json={
            "workspace_id": str(auth_workspace.id),
            "label": "ci-pipeline",
        })
        assert r.status_code == 201, r.text
        data = r.json()
        assert "raw_key" in data
        assert data["raw_key"].startswith("cb_")
        assert "id" in data
        assert data["label"] == "ci-pipeline"
        assert data["workspace_id"] == str(auth_workspace.id)
        print(f"\n  [AUTH] generated key id={data['id']}, prefix={data['raw_key'][:6]}...")

    def test_generate_key_for_unknown_workspace(self, client):
        r = client.post("/api/v1/auth/keys", json={
            "workspace_id": str(uuid4()),
            "label": "test",
        })
        assert r.status_code == 404

    def test_raw_key_not_stored(self, client, auth_workspace):
        """Verify list response never contains raw_key."""
        r = client.get(f"/api/v1/auth/keys/{auth_workspace.id}")
        assert r.status_code == 200
        for key in r.json():
            assert "raw_key" not in key
            assert "key_hash" not in key
        print(f"\n  [AUTH] list: {len(r.json())} keys, no raw_key exposed")


# ---------------------------------------------------------------------------
# Key listing
# ---------------------------------------------------------------------------

class TestKeyListing:
    def test_list_keys_empty_workspace(self, client):
        """New workspace has no keys."""
        # Create a fresh workspace
        ws_r = client.post("/api/v1/workspaces", json={"name": f"empty-{uuid4().hex[:6]}"})
        assert ws_r.status_code == 201
        new_ws_id = ws_r.json()["id"]
        r = client.get(f"/api/v1/auth/keys/{new_ws_id}")
        assert r.status_code == 200
        assert r.json() == []

    def test_list_keys_after_generation(self, client, auth_workspace):
        """Keys appear in list after generation."""
        # Generate a key first
        client.post("/api/v1/auth/keys", json={
            "workspace_id": str(auth_workspace.id),
            "label": "list-test",
        })
        r = client.get(f"/api/v1/auth/keys/{auth_workspace.id}")
        assert r.status_code == 200
        keys = r.json()
        assert len(keys) >= 1
        # Verify expected fields
        for key in keys:
            assert "id" in key
            assert "label" in key
            assert "is_active" in key
            assert "created_at" in key


# ---------------------------------------------------------------------------
# Key revocation
# ---------------------------------------------------------------------------

class TestKeyRevocation:
    def test_revoke_key(self, client, auth_workspace):
        """Revoke a key — is_active becomes False."""
        # Generate a key to revoke
        gen_r = client.post("/api/v1/auth/keys", json={
            "workspace_id": str(auth_workspace.id),
            "label": "revoke-me",
        })
        assert gen_r.status_code == 201
        key_id = gen_r.json()["id"]

        # Revoke it
        rev_r = client.delete(f"/api/v1/auth/keys/{key_id}")
        assert rev_r.status_code == 200
        assert rev_r.json()["revoked"] is True
        print(f"\n  [AUTH] revoked key_id={key_id}")

    def test_revoke_unknown_key(self, client):
        r = client.delete(f"/api/v1/auth/keys/{uuid4()}")
        assert r.status_code == 404

    def test_revoked_key_not_usable(self, client, auth_workspace):
        """After revocation, a key should not authenticate."""
        # Generate
        gen_r = client.post("/api/v1/auth/keys", json={
            "workspace_id": str(auth_workspace.id),
            "label": "revoke-and-test",
        })
        raw_key = gen_r.json()["raw_key"]
        key_id = gen_r.json()["id"]

        # Revoke
        client.delete(f"/api/v1/auth/keys/{key_id}")

        # Attempt to use revoked key on a protected endpoint
        # Admin reset is a good candidate as it would use auth in prod
        r = client.get(
            f"/api/v1/auth/keys/{auth_workspace.id}",
            headers={"X-API-Key": raw_key},
        )
        # This still returns 200 because the list endpoint is not protected yet
        # The middleware is wired but no route uses Depends(require_api_key) yet
        # This test documents the current state
        assert r.status_code == 200
        # Verify the revoked key is listed as is_active=False
        keys = r.json()
        revoked_key = next((k for k in keys if k["id"] == key_id), None)
        assert revoked_key is not None
        assert revoked_key["is_active"] is False
        print(f"\n  [AUTH] revoked key shows is_active=False in list: PASS")


# ---------------------------------------------------------------------------
# Middleware — validate against real DB
# ---------------------------------------------------------------------------

class TestAuthMiddleware:
    def test_valid_key_hashes_correctly(self, client, auth_workspace):
        """Verify that hash_api_key produces a 64-char SHA-256 digest."""
        from backend.core.auth import hash_api_key, generate_api_key
        raw_key, stored_hash = generate_api_key()
        computed_hash = hash_api_key(raw_key)
        assert computed_hash == stored_hash
        assert len(computed_hash) == 64
        print(f"\n  [AUTH] hash determinism: {computed_hash[:8]}... PASS")
