# tests/integration/ingestion/test_worker.py
# Integration tests for IngestionWorker — requires running PostgreSQL.
# Run: pytest tests/integration/ingestion/test_worker.py -v
#
# These tests call worker._execute() directly (bypassing BackgroundTasks)
# so they can reuse the test session and assert on DB state.

import pytest
import pytest_asyncio
from uuid import uuid4
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.db.session import get_engine
from backend.core.config import get_settings
from backend.db.repositories.workspace_repo import workspace_repo
from backend.db.repositories.event_repo import event_repo
from backend.db.repositories.ingestion_repo import ingestion_repo
from backend.db.repositories.entity_registry_repo import entity_registry_repo
from backend.ingestion.adapters.synthetic import SyntheticAdapter
from backend.ingestion.deduplicator import Deduplicator
from backend.ingestion.entity_extractor import BasicEntityExtractor
from backend.ingestion.schemas import RawEvent
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
    slug = f"worker-test-{uuid4()}"
    ws = await workspace_repo.create(session, name="Worker Test Workspace", slug=slug)
    return ws


@pytest_asyncio.fixture
def worker():
    return IngestionWorker(
        adapter=SyntheticAdapter(events=[]),
        deduplicator=Deduplicator(),
        extractor=BasicEntityExtractor(
            service_names=["auth-service", "payment-gateway"],
            team_names=["platform-team"],
        ),
        event_repo=event_repo,
        ingestion_repo=ingestion_repo,
        entity_registry_repo=entity_registry_repo,
    )


def make_slack_raw(source_id: str = "msg-001", content: str = "auth-service is down") -> RawEvent:
    return RawEvent(
        source=SourceType.SLACK,
        source_id=source_id,
        raw_content=content,
        raw_author="alice",
        raw_timestamp="2025-01-15T14:22:00Z",
        extra={"channel": "incidents"},
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_worker_creates_job_and_completes(session, workspace, worker):
    """Full happy path: one Slack event → job COMPLETED, event in DB."""
    job = await ingestion_repo.create_job(
        session=session,
        workspace_id=workspace.id,
        source=SourceType.SLACK,
        source_config={"mode": "synthetic"},
        requested_by="test",
    )

    raw = [make_slack_raw()]
    worker.adapter = SyntheticAdapter(events=raw)
    await worker._execute(job.id, session)

    completed_job = await ingestion_repo.get_by_id(session, job.id)
    assert completed_job.status == IngestionStatus.COMPLETED
    assert completed_job.events_ingested == 1
    assert completed_job.events_failed == 0
    assert completed_job.processing_time_ms is not None


async def test_worker_writes_event_to_db(session, workspace, worker):
    """After a successful run the event row must exist in the events table."""
    job = await ingestion_repo.create_job(
        session=session,
        workspace_id=workspace.id,
        source=SourceType.SLACK,
        source_config={},
        requested_by="test",
    )
    raw = [make_slack_raw(source_id="unique-msg-abc")]
    worker.adapter = SyntheticAdapter(events=raw)
    await worker._execute(job.id, session)

    # Fetch the event from DB by source + source_id
    from sqlalchemy import select
    from backend.db.models.event import EventModel
    stmt = (
        select(EventModel)
        .where(EventModel.workspace_id == workspace.id)
        .where(EventModel.source == SourceType.SLACK)
        .where(EventModel.source_id == "unique-msg-abc")
    )
    result = await session.execute(stmt)
    event = result.scalar_one_or_none()
    assert event is not None
    assert "auth-service" in event.content


async def test_worker_registers_extracted_entities(session, workspace, worker):
    """Entities mentioned in the event text must appear in entity_registry."""
    job = await ingestion_repo.create_job(
        session=session,
        workspace_id=workspace.id,
        source=SourceType.SLACK,
        source_config={},
        requested_by="test",
    )
    raw = [make_slack_raw(content="auth-service latency is spiking", source_id="msg-ent-001")]
    worker.adapter = SyntheticAdapter(events=raw)
    await worker._execute(job.id, session)

    from sqlalchemy import select
    from backend.db.models.entity_registry import EntityRegistryModel
    stmt = (
        select(EntityRegistryModel)
        .where(EntityRegistryModel.workspace_id == workspace.id)
        .where(EntityRegistryModel.canonical_name == "auth-service")
    )
    result = await session.execute(stmt)
    entity = result.scalar_one_or_none()
    assert entity is not None
    assert entity.source_event_count >= 1


async def test_worker_skips_duplicate_event(session, workspace, worker):
    """If the same event is submitted twice, events_ingested stays at 1."""
    job1 = await ingestion_repo.create_job(
        session=session,
        workspace_id=workspace.id,
        source=SourceType.SLACK,
        source_config={},
        requested_by="test",
    )
    raw = [make_slack_raw(source_id="dedup-msg-001")]
    worker.adapter = SyntheticAdapter(events=raw)
    await worker._execute(job1.id, session)

    # Submit the same event again (adapter already has the events)
    job2 = await ingestion_repo.create_job(
        session=session,
        workspace_id=workspace.id,
        source=SourceType.SLACK,
        source_config={},
        requested_by="test",
    )
    await worker._execute(job2.id, session)

    job2_result = await ingestion_repo.get_by_id(session, job2.id)
    # Duplicate was skipped — not ingested, not failed
    assert job2_result.status == IngestionStatus.COMPLETED
    assert job2_result.events_ingested == 0
    assert job2_result.events_failed == 0


async def test_worker_processes_multiple_events(session, workspace, worker):
    """Worker must process all events in the batch, not just the first."""
    job = await ingestion_repo.create_job(
        session=session,
        workspace_id=workspace.id,
        source=SourceType.SLACK,
        source_config={},
        requested_by="test",
    )
    raw = [
        make_slack_raw(source_id="batch-001", content="auth-service is down"),
        make_slack_raw(source_id="batch-002", content="payment-gateway is slow"),
        make_slack_raw(source_id="batch-003", content="no entities here"),
    ]
    worker.adapter = SyntheticAdapter(events=raw)
    await worker._execute(job.id, session)

    completed_job = await ingestion_repo.get_by_id(session, job.id)
    assert completed_job.events_ingested == 3
    assert completed_job.events_failed == 0


async def test_worker_marks_job_failed_on_unhandled_error(session, workspace):
    """If the adapter raises an unhandled exception, the job must be marked FAILED."""
    from unittest.mock import AsyncMock

    broken_adapter = AsyncMock()
    broken_adapter.fetch_events.side_effect = RuntimeError("Adapter exploded")

    broken_worker = IngestionWorker(
        adapter=broken_adapter,
        deduplicator=Deduplicator(),
        extractor=BasicEntityExtractor(service_names=[], team_names=[]),
        event_repo=event_repo,
        ingestion_repo=ingestion_repo,
        entity_registry_repo=entity_registry_repo,
    )

    job = await ingestion_repo.create_job(
        session=session,
        workspace_id=workspace.id,
        source=SourceType.SLACK,
        source_config={},
        requested_by="test",
    )
    raw = [make_slack_raw()]
    # the broken_adapter ignores `raw` anyway since it's a mock
    await broken_worker._execute(job.id, session)

    failed_job = await ingestion_repo.get_by_id(session, job.id)
    assert failed_job.status == IngestionStatus.FAILED
    assert "Adapter exploded" in failed_job.error_message


async def test_worker_handles_github_event(session, workspace, worker):
    """Worker must normalise GitHub events correctly (different normalizer path)."""
    job = await ingestion_repo.create_job(
        session=session,
        workspace_id=workspace.id,
        source=SourceType.GITHUB,
        source_config={},
        requested_by="test",
    )
    raw = [
        RawEvent(
            source=SourceType.GITHUB,
            source_id="pr-42",
            raw_content="Switch auth-service session store to Redis for horizontal scaling.",
            raw_author="bob",
            raw_timestamp="2025-01-20T09:00:00Z",
            extra={"repo": "auth-service", "pr_number": 42, "title": "Switch to Redis"},
        )
    ]
    worker.adapter = SyntheticAdapter(events=raw)
    await worker._execute(job.id, session)

    completed_job = await ingestion_repo.get_by_id(session, job.id)
    assert completed_job.events_ingested == 1

    # Title should be built correctly
    from sqlalchemy import select
    from backend.db.models.event import EventModel
    stmt = (
        select(EventModel)
        .where(EventModel.workspace_id == workspace.id)
        .where(EventModel.source == SourceType.GITHUB)
        .where(EventModel.source_id == "pr-42")
    )
    result = await session.execute(stmt)
    event = result.scalar_one_or_none()
    assert event is not None
    assert event.title == "[auth-service] PR #42: Switch to Redis"
