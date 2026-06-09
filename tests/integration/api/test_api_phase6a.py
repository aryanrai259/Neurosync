"""Integration tests for Phase 6A API endpoints.

Uses the synchronous TestClient (same pattern as existing integration tests)
to avoid asyncpg event-loop conflicts.
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
# Module-scoped fixtures (same pattern as test_ingest_api.py)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def client():
    """Synchronous TestClient for the FastAPI app.

    Disposes the global async engine after the module finishes to prevent
    asyncpg event-loop contamination between test modules on Windows.
    """
    from backend.db.session import engine as db_engine
    with TestClient(app) as c:
        yield c
    # Synchronously dispose to clear stale connections from the proactor loop
    import asyncio
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
async def api_workspace(db_session):
    """Create a test workspace once per module."""
    ws = await workspace_repo.create(db_session, name=f"api-test-{uuid4().hex[:8]}")
    await db_session.commit()
    await db_session.refresh(ws)
    return ws


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def api_key_header(db_session, api_workspace):
    """Generate a valid API key for the module workspace and return its header."""
    from backend.core.auth import generate_api_key
    from backend.db.repositories.api_key_repo import api_key_repo
    raw_key, key_hash = generate_api_key()
    await api_key_repo.create_key(db_session, api_workspace.id, key_hash, "Test Key")
    await db_session.commit()
    return {"X-API-Key": raw_key}

# ---------------------------------------------------------------------------

# Health Endpoints
# ---------------------------------------------------------------------------

def test_liveness_health(client):
    """GET /health should return 200 and status ok."""
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "version" in data


def test_deep_health_returns_components(client):
    """GET /api/v1/health/deep should return per-component status."""
    resp = client.get("/api/v1/health/deep")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "components" in data
    assert "postgres" in data["components"]
    assert "neo4j" in data["components"]


def test_deep_health_postgres_ok(client):
    """PostgreSQL should be healthy in the test environment."""
    resp = client.get("/api/v1/health/deep")
    data = resp.json()
    assert data["components"]["postgres"]["status"] == "ok"


# ---------------------------------------------------------------------------
# Workspace Endpoints
# ---------------------------------------------------------------------------

def test_create_workspace_returns_201(client):
    """POST /api/v1/workspaces creates a workspace with 201."""
    unique_name = f"ws-create-{uuid4().hex[:8]}"
    resp = client.post("/api/v1/workspaces", json={"name": unique_name})
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["name"] == unique_name
    assert "id" in data


def test_get_workspace_by_id(client, api_workspace):
    """GET /api/v1/workspaces/{id} returns the workspace."""
    resp = client.get(f"/api/v1/workspaces/{api_workspace.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert str(data["id"]) == str(api_workspace.id)


def test_get_workspace_not_found(client):
    """GET /api/v1/workspaces/{id} returns 404 for unknown ID."""
    resp = client.get(f"/api/v1/workspaces/{uuid4()}")
    assert resp.status_code == 404


def test_list_workspaces_returns_list(client):
    """GET /api/v1/workspaces returns a list."""
    resp = client.get("/api/v1/workspaces")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    assert len(resp.json()) >= 1


# ---------------------------------------------------------------------------
# Jobs Endpoint
# ---------------------------------------------------------------------------

def test_get_job_not_found(client):
    """GET /api/v1/jobs/{id} returns 404 for unknown job."""
    resp = client.get(f"/api/v1/jobs/{uuid4()}")
    assert resp.status_code == 404


def test_get_job_after_ingest(client, api_workspace, api_key_header):
    """Submitting a synthetic job creates a trackable job_id."""
    ingest_resp = client.post(
        "/api/v1/ingest/synthetic",
        headers=api_key_header,
        json={
            "workspace_id": str(api_workspace.id),
            "requested_by": "test",
            "events": [
                {
                    "source": "slack",
                    "source_id": f"msg-{uuid4().hex[:8]}",
                    "raw_content": "auth-service deployment complete",
                    "raw_author": "alice",
                    "raw_timestamp": "2026-01-15T14:22:00Z",
                }
            ],
        },
    )
    assert ingest_resp.status_code == 202, ingest_resp.text
    job_id = ingest_resp.json()["job_id"]

    job_resp = client.get(f"/api/v1/jobs/{job_id}")
    assert job_resp.status_code == 200
    job_data = job_resp.json()
    assert job_data["job_id"] == job_id
    assert job_data["status"].upper() in ("PENDING", "PROCESSING", "COMPLETED", "FAILED")


# ---------------------------------------------------------------------------
# Admin Endpoints
# ---------------------------------------------------------------------------

def test_reset_workspace_not_found(client, api_key_header):
    """POST /api/v1/admin/reset/{id} returns 404 for unknown workspace."""
    resp = client.post(f"/api/v1/admin/reset/{uuid4()}", headers=api_key_header)
    assert resp.status_code == 404


def test_reset_workspace_accepted(client, api_workspace, api_key_header):
    """POST /api/v1/admin/reset/{workspace_id} returns 202 for valid workspace."""
    resp = client.post(f"/api/v1/admin/reset/{api_workspace.id}", headers=api_key_header)
    assert resp.status_code == 202
    data = resp.json()
    assert data["status"] == "accepted"


def test_reindex_workspace_not_found(client, api_key_header):
    """POST /api/v1/admin/reindex/{id} returns 404 for unknown workspace."""
    resp = client.post(f"/api/v1/admin/reindex/{uuid4()}", headers=api_key_header)
    assert resp.status_code == 404


def test_reindex_workspace_accepted(client, api_workspace, api_key_header):
    """POST /api/v1/admin/reindex/{workspace_id} returns 202 for valid workspace."""
    resp = client.post(f"/api/v1/admin/reindex/{api_workspace.id}", headers=api_key_header)
    assert resp.status_code == 202
    data = resp.json()
    assert data["status"] == "accepted"
    assert "events_queued" in data
