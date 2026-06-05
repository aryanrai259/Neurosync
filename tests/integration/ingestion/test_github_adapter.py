# tests/integration/ingestion/test_github_adapter.py
import json
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import httpx
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.core.config import get_settings
from backend.db.repositories.entity_registry_repo import entity_registry_repo
from backend.db.repositories.event_repo import event_repo
from backend.db.repositories.ingestion_repo import ingestion_repo
from backend.db.repositories.workspace_repo import workspace_repo
from backend.db.session import get_engine
from backend.ingestion.adapters.github import GitHubAdapter
from backend.ingestion.deduplicator import Deduplicator
from backend.ingestion.entity_extractor import BasicEntityExtractor
from backend.ingestion.worker import IngestionWorker
from backend.models.enums import IngestionStatus, SourceType

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def session() -> AsyncSession:
    engine = get_engine(get_settings().database_url)
    maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as s:
        yield s
    await engine.dispose()


@pytest_asyncio.fixture
async def workspace(session):
    slug = f"gh-test-{uuid4()}"
    ws = await workspace_repo.create(session, name="GitHub Adapter Test", slug=slug)
    return ws


# ---------------------------------------------------------------------------
# Adapter Fetch Tests (Mocked)
# ---------------------------------------------------------------------------

async def test_github_adapter_fetches_and_converts():
    """Adapter must correctly fetch data via httpx and construct RawEvents."""
    from unittest.mock import MagicMock
    mock_response = MagicMock()
    mock_response.json.return_value = [
        {
            "number": 101,
            "title": "Bug in auth-service",
            "body": "The auth-service is failing on startup.",
            "user": {"login": "testuser"},
            "created_at": "2025-01-01T12:00:00Z",
            "html_url": "https://github.com/owner/repo/issues/101",
            "labels": [{"name": "bug"}],
        },
        {
            "number": 102,
            "title": "Fix auth-service",
            "body": "Fixes #101",
            "user": {"login": "dev1"},
            "created_at": "2025-01-02T12:00:00Z",
            "html_url": "https://github.com/owner/repo/pull/102",
            "pull_request": {"url": "..."},
            "labels": [],
        }
    ]
    mock_response.raise_for_status.return_value = None

    adapter = GitHubAdapter(repo="owner/repo", limit=2)
    
    mock_get = AsyncMock(return_value=mock_response)
    with patch("httpx.AsyncClient.get", new=mock_get):
        events = await adapter.fetch_events()

    assert mock_get.called
    assert len(events) == 2

    # Issue
    assert events[0].source == SourceType.GITHUB
    assert events[0].source_id == "101"
    assert events[0].raw_content == "The auth-service is failing on startup."
    assert events[0].raw_author == "testuser"
    assert events[0].extra["is_pr"] is False
    assert events[0].extra["title"] == "Bug in auth-service"
    assert "bug" in events[0].extra["labels"]

    # PR
    assert events[1].source_id == "102"
    assert events[1].extra["is_pr"] is True


async def test_github_adapter_raises_on_http_error():
    """Adapter must raise httpx exceptions on failure to allow worker to mark FAILED."""
    adapter = GitHubAdapter(repo="bad/repo", limit=1)

    mock_response = httpx.Response(404, request=httpx.Request("GET", "https://api.github.com"))
    with patch("httpx.AsyncClient.get", side_effect=httpx.HTTPStatusError("404", request=mock_response.request, response=mock_response)):
        with pytest.raises(httpx.HTTPStatusError):
            await adapter.fetch_events()


# ---------------------------------------------------------------------------
# Duplicate Ingestion End-to-End Test (Mocked Adapter + Real DB)
# ---------------------------------------------------------------------------

async def test_github_pipeline_duplicate_ingestion(session, workspace):
    """
    Simulates the full worker flow running twice on the same GitHub events.
    Verifies the deduplicator catches them and DB count stays the same.
    """
    from unittest.mock import MagicMock
    mock_response = MagicMock()
    mock_response.json.return_value = [
        {
            "number": 999,
            "title": "Duplicate Test Issue",
            "body": "Checking deduplication logic for auth-service.",
            "user": {"login": "tester"},
            "created_at": "2025-01-01T12:00:00Z",
            "html_url": "https://github.com/owner/repo/issues/999",
            "labels": [],
        }
    ]
    mock_response.raise_for_status.return_value = None

    adapter = GitHubAdapter(repo="owner/repo")
    worker = IngestionWorker(
        adapter=adapter,
        deduplicator=Deduplicator(),
        extractor=BasicEntityExtractor(service_names=["auth-service"], team_names=[]),
        event_repo=event_repo,
        ingestion_repo=ingestion_repo,
        entity_registry_repo=entity_registry_repo,
    )

    mock_get = AsyncMock(return_value=mock_response)
    with patch("httpx.AsyncClient.get", new=mock_get):
        # Run 1
        job1 = await ingestion_repo.create_job(
            session, workspace.id, SourceType.GITHUB, {"repo": "owner/repo"}, "test"
        )
        await worker._execute(job1.id, session)

        completed1 = await ingestion_repo.get_by_id(session, job1.id)
        assert completed1.status == IngestionStatus.COMPLETED
        assert completed1.events_ingested == 1
        assert completed1.events_failed == 0

        # Run 2
        job2 = await ingestion_repo.create_job(
            session, workspace.id, SourceType.GITHUB, {"repo": "owner/repo"}, "test"
        )
        await worker._execute(job2.id, session)

        completed2 = await ingestion_repo.get_by_id(session, job2.id)
        assert completed2.status == IngestionStatus.COMPLETED
        assert completed2.events_ingested == 0  # Deduplicated!
        assert completed2.events_failed == 0

    # Verify exactly 1 event in DB
    from sqlalchemy import select
    from backend.db.models.event import EventModel
    stmt = select(EventModel).where(EventModel.workspace_id == workspace.id)
    result = await session.execute(stmt)
    db_events = result.scalars().all()
    assert len(db_events) == 1
    assert db_events[0].source_id == "999"
    assert db_events[0].source == SourceType.GITHUB
