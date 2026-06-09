# tests/integration/ingestion/test_ingest_api.py
# Integration tests for POST /api/v1/ingest/synthetic.
# Uses FastAPI TestClient + real PostgreSQL (docker-compose up -d first).
# Run: pytest tests/integration/ingestion/test_ingest_api.py -v

from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.core.config import get_settings
from backend.db.repositories.workspace_repo import workspace_repo
from backend.db.session import get_engine
from backend.main import app

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def client():
    """Synchronous TestClient for the FastAPI app."""
    with TestClient(app) as c:
        yield c


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def db_session():
    engine = get_engine(get_settings().database_url)
    maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as s:
        yield s
    await engine.dispose()


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def test_workspace(db_session):
    """Create a workspace once for all tests in this module."""
    slug = f"api-test-{uuid4()}"
    ws = await workspace_repo.create(db_session, name="API Test Workspace", slug=slug)
    return ws


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def api_key_header(db_session, test_workspace):
    """Generate a valid API key for the module workspace and return its header."""
    from backend.core.auth import generate_api_key
    from backend.db.repositories.api_key_repo import api_key_repo
    raw_key, key_hash = generate_api_key()
    await api_key_repo.create_key(db_session, test_workspace.id, key_hash, "Test Key")
    await db_session.commit()
    return {"X-API-Key": raw_key}


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def synthetic_payload(workspace_id, events=None):
    """Build a minimal SyntheticJobRequest body."""
    events = events or [
        {
            "source": "slack",
            "source_id": f"msg-{uuid4()}",
            "raw_content": "auth-service is down",
            "raw_author": "alice",
            "raw_timestamp": "2025-01-15T14:22:00Z",
            "extra": {"channel": "incidents"},
        }
    ]
    return {
        "workspace_id": str(workspace_id),
        "requested_by": "test-runner",
        "events": events,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSubmitSyntheticJob:
    def test_returns_202(self, client, test_workspace, api_key_header):
        payload = synthetic_payload(test_workspace.id)
        response = client.post("/api/v1/ingest/synthetic", json=payload, headers=api_key_header)
        assert response.status_code == 202

    def test_response_has_job_id(self, client, test_workspace, api_key_header):
        payload = synthetic_payload(test_workspace.id)
        response = client.post("/api/v1/ingest/synthetic", json=payload, headers=api_key_header)
        data = response.json()
        assert "job_id" in data
        # Should be a valid UUID
        from uuid import UUID
        UUID(data["job_id"])  # raises ValueError if invalid

    def test_response_status_is_pending(self, client, test_workspace, api_key_header):
        payload = synthetic_payload(test_workspace.id)
        response = client.post("/api/v1/ingest/synthetic", json=payload, headers=api_key_header)
        data = response.json()
        assert data["status"] == "pending"

    def test_response_event_count_matches_input(self, client, test_workspace, api_key_header):
        events = [
            {
                "source": "slack",
                "source_id": f"msg-count-{i}",
                "raw_content": "test message",
                "raw_author": "alice",
                "raw_timestamp": "2025-01-15T14:22:00Z",
            }
            for i in range(3)
        ]
        payload = synthetic_payload(test_workspace.id, events=events)
        response = client.post("/api/v1/ingest/synthetic", json=payload, headers=api_key_header)
        data = response.json()
        assert data["event_count"] == 3

    def test_returns_404_for_unknown_workspace(self, client, api_key_header):
        payload = synthetic_payload(uuid4())
        response = client.post("/api/v1/ingest/synthetic", json=payload, headers=api_key_header)
        assert response.status_code == 404

    def test_returns_422_for_empty_events_list(self, client, test_workspace, api_key_header):
        """Pydantic validator (min_length=1 on events list) must reject empty list."""
        payload = {
            "workspace_id": str(test_workspace.id),
            "requested_by": "test",
            "events": [],
        }
        response = client.post("/api/v1/ingest/synthetic", json=payload, headers=api_key_header)
        assert response.status_code == 422

    def test_returns_422_for_missing_workspace_id(self, client, api_key_header):
        payload = {
            "requested_by": "test",
            "events": [
                {
                    "source": "slack",
                    "source_id": "x",
                    "raw_content": "y",
                    "raw_author": "z",
                    "raw_timestamp": "2025-01-01T00:00:00Z",
                }
            ],
        }
        response = client.post("/api/v1/ingest/synthetic", json=payload, headers=api_key_header)
        assert response.status_code == 422

    def test_health_endpoint_returns_200(self, client):
        """Sanity check: the server itself is healthy."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


class TestSubmitGithubJob:
    def test_returns_202_accepted(self, client, test_workspace, api_key_header):
        payload = {
            "workspace_id": str(test_workspace.id),
            "requested_by": "test-user",
            "repo": "owner/repo",
        }
        resp = client.post("/api/v1/ingest/github", json=payload, headers=api_key_header)
        assert resp.status_code == 202
        data = resp.json()
        assert data["status"] == "pending"
        assert "job_id" in data

    def test_404_on_missing_workspace(self, client, api_key_header):
        payload = {
            "workspace_id": str(uuid4()),
            "requested_by": "test-user",
            "repo": "owner/repo",
        }
        resp = client.post("/api/v1/ingest/github", json=payload, headers=api_key_header)
        assert resp.status_code == 404

    def test_422_on_invalid_repo(self, client, test_workspace, api_key_header):
        payload = {
            "workspace_id": str(test_workspace.id),
            "requested_by": "test-user",
            "repo": "a",  # min_length=3
        }
        resp = client.post("/api/v1/ingest/github", json=payload, headers=api_key_header)
        assert resp.status_code == 422
