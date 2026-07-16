# tests/integration/api/test_timeline_api.py
# Integration tests for GET /api/v1/timeline/{workspace_id}/entity/{entity_id}.
# Uses FastAPI TestClient + real PostgreSQL (docker-compose up -d first).
# Run: pytest tests/integration/api/test_timeline_api.py -v
#
# Regression coverage: backend/db/repositories/timeline_repo.py referenced
# EventModel.event_timestamp and EventModel.raw_content, neither of which
# exist (real columns are `timestamp` and `content`) — every call to this
# endpoint 500'd with AttributeError. This file did not exist before, which
# is why the bug shipped untested despite the module's own header comment
# referencing it as the test file.

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

pytestmark = pytest.mark.asyncio


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
    slug = f"timeline-test-{uuid4()}"
    ws = await workspace_repo.create(db_session, name="Timeline Test Workspace", slug=slug)
    return ws


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def entity_with_events(db_session, test_workspace):
    """Insert an entity plus a couple of events mentioning it by name."""
    from backend.db.models.entity_registry import EntityRegistryModel
    from backend.db.models.event import EventModel
    from backend.models.enums import EntityType

    entity = EntityRegistryModel(
        id=uuid4(),
        workspace_id=test_workspace.id,
        entity_type=EntityType.SERVICE,
        canonical_name="payment-gateway",
    )
    db_session.add(entity)

    events = [
        EventModel(
            id=uuid4(),
            workspace_id=test_workspace.id,
            source=SourceType.SLACK,
            source_id=f"timeline-msg-{i}-{uuid4()}",
            content=f"payment-gateway incident update #{i}",
            author_id="dana",
            timestamp=datetime(2026, 1, i + 1, tzinfo=timezone.utc),
            metadata_json={},
        )
        for i in range(3)
    ]
    for e in events:
        db_session.add(e)
    await db_session.commit()
    await db_session.refresh(entity)
    return entity


class TestTimelineEntityEndpoint:
    def test_returns_200_not_500(self, client, test_workspace, entity_with_events):
        response = client.get(
            f"/api/v1/timeline/{test_workspace.id}/entity/{entity_with_events.id}"
        )
        assert response.status_code == 200, (
            f"expected 200, got {response.status_code}: {response.text} — "
            "if this is a 500 with AttributeError on EventModel, the column-name "
            "regression in timeline_repo.py has resurfaced"
        )

    def test_finds_events_mentioning_the_entity(self, client, test_workspace, entity_with_events):
        response = client.get(
            f"/api/v1/timeline/{test_workspace.id}/entity/{entity_with_events.id}",
            params={"days_back": 365},
        )
        data = response.json()
        assert data["total_events"] >= 3

    def test_summary_endpoint_returns_200(self, client, test_workspace, entity_with_events):
        response = client.get(
            f"/api/v1/timeline/{test_workspace.id}/entity/{entity_with_events.id}/summary",
            params={"days_back": 365},
        )
        assert response.status_code == 200

    def test_returns_empty_for_unknown_entity(self, client, test_workspace):
        response = client.get(f"/api/v1/timeline/{test_workspace.id}/entity/{uuid4()}")
        assert response.status_code == 200
        assert response.json()["total_events"] == 0
