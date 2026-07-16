# tests/integration/api/test_admin.py
# Integration tests for POST /api/v1/admin/{reset,reindex}.
# Uses FastAPI TestClient + real PostgreSQL + Neo4j (docker-compose up -d first).
# Run: pytest tests/integration/api/test_admin.py -v
#
# Regression coverage: _run_reindex() previously crashed on every call with
# `VectorIndexer.__init__() got an unexpected keyword argument 'vector_repo'`
# (wrong kwarg name) and called a nonexistent `index_event()` method. This
# file did not exist before, despite being referenced in admin.py's own
# header comment — that gap is why the crash shipped untested.

from datetime import datetime, timezone
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.core.config import get_settings
from backend.db.repositories.workspace_repo import workspace_repo
from backend.db.session import get_engine
from backend.main import app
from backend.models.enums import SourceType

pytestmark = pytest.mark.asyncio(loop_scope="module")


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest_asyncio.fixture(autouse=True, scope="module", loop_scope="module")
async def _dispose_global_engine_after_module():
    """
    Dispose the app's global engine after this module finishes so the next
    test module's TestClient (its own portal loop) gets fresh connections
    instead of reusing pooled connections bound to this module's loop.
    Mirrors tests/e2e/reasoning/conftest.py's established pattern.
    """
    yield
    from backend.db.session import engine

    await engine.dispose()


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def db_session():
    engine = get_engine(get_settings().database_url)
    maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as s:
        yield s
    await engine.dispose()


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def test_workspace(db_session):
    slug = f"admin-test-{uuid4()}"
    ws = await workspace_repo.create(db_session, name="Admin Test Workspace", slug=slug)
    return ws


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def api_key_header(db_session, test_workspace):
    from backend.core.auth import generate_api_key
    from backend.db.repositories.api_key_repo import api_key_repo

    raw_key, key_hash = generate_api_key()
    await api_key_repo.create_key(db_session, test_workspace.id, key_hash, "Admin Test Key")
    await db_session.commit()
    return {"X-API-Key": raw_key}


async def _insert_pending_event(db_session, workspace_id, source_id: str):
    """Insert an EventModel directly with embedding_status=PENDING, bypassing ingestion."""
    from backend.db.models.event import EventModel
    from backend.models.enums import EmbeddingStatus

    event = EventModel(
        id=uuid4(),
        workspace_id=workspace_id,
        source=SourceType.SLACK,
        source_id=source_id,
        content="payment-gateway latency spiked after the last deploy",
        author_id="carol",
        timestamp=datetime.now(timezone.utc),
        metadata_json={},
        embedding_status=EmbeddingStatus.PENDING,
    )
    db_session.add(event)
    await db_session.commit()
    await db_session.refresh(event)
    return event


class TestReindex:
    async def test_reindex_returns_202_with_queued_count(
        self, client, test_workspace, api_key_header, db_session
    ):
        event = await _insert_pending_event(db_session, test_workspace.id, f"pending-{uuid4()}")

        response = client.post(
            f"/api/v1/admin/reindex/{test_workspace.id}", headers=api_key_header
        )
        assert response.status_code == 202
        data = response.json()
        assert data["events_queued"] >= 1

        # Background reindex task must complete without raising before
        # TestClient returns control (BackgroundTasks run synchronously).
        from sqlalchemy import select
        from backend.db.models.event import EventModel
        from backend.db.models.event_embedding import EventEmbeddingModel
        from backend.models.enums import EmbeddingStatus

        await db_session.refresh(event)
        stmt = select(EventModel).where(EventModel.id == event.id)
        refreshed = (await db_session.execute(stmt)).scalar_one()
        assert refreshed.embedding_status == EmbeddingStatus.EMBEDDED, (
            "reindex should mark the previously-PENDING event EMBEDDED — "
            "if this fails, VectorIndexer is being constructed/called incorrectly again"
        )

        emb_stmt = select(EventEmbeddingModel).where(EventEmbeddingModel.event_id == event.id)
        embedding = (await db_session.execute(emb_stmt)).scalar_one_or_none()
        assert embedding is not None

    async def test_reindex_returns_404_for_unknown_workspace(self, client, api_key_header):
        response = client.post(f"/api/v1/admin/reindex/{uuid4()}", headers=api_key_header)
        assert response.status_code == 404

    async def test_reindex_requires_api_key(self, client, test_workspace):
        response = client.post(f"/api/v1/admin/reindex/{test_workspace.id}")
        assert response.status_code == 401
