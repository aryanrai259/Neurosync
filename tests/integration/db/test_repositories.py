import pytest
import pytest_asyncio
from uuid import uuid4
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker

from backend.db.session import get_engine, get_settings
from backend.db.repositories.workspace_repo import workspace_repo
from backend.db.repositories.event_repo import event_repo
from backend.db.repositories.ingestion_repo import ingestion_repo
from backend.db.repositories.entity_registry_repo import entity_registry_repo
from backend.models.enums import SourceType, EntityType, IngestionStatus

pytestmark = pytest.mark.asyncio

@pytest_asyncio.fixture
async def session() -> AsyncSession:
    """Fixture that provides a database session."""
    engine = get_engine(get_settings().database_url)
    session_maker = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_maker() as session:
        yield session
    await engine.dispose()


async def test_workspace_repository(session: AsyncSession):
    # Create
    slug = f"test-workspace-{uuid4()}"
    workspace = await workspace_repo.create(session, name="Test Workspace", slug=slug)
    assert workspace.id is not None
    assert workspace.slug == slug
    assert workspace.is_active is True

    # Get by slug
    fetched = await workspace_repo.get_by_slug(session, slug)
    assert fetched is not None
    assert fetched.id == workspace.id

    # Get by id
    fetched_by_id = await workspace_repo.get_by_id(session, workspace.id)
    assert fetched_by_id is not None

    # Exists
    assert await workspace_repo.exists(session, workspace.id) is True

    # Delete
    await workspace_repo.delete(session, workspace.id)
    await session.commit()
    assert await workspace_repo.exists(session, workspace.id) is False


async def test_event_repository(session: AsyncSession):
    # Setup workspace
    workspace = await workspace_repo.create(session, name="Evt Test", slug=f"evt-{uuid4()}")
    
    # Upsert event
    ts = datetime.now(timezone.utc)
    event = await event_repo.upsert_event(
        session=session,
        workspace_id=workspace.id,
        source=SourceType.GITHUB,
        source_id="commit-123",
        content="Fixed the auth bug",
        author_id="user-123",
        timestamp=ts,
    )
    assert event.id is not None
    assert event.content == "Fixed the auth bug"

    # Upsert again (update)
    event2 = await event_repo.upsert_event(
        session=session,
        workspace_id=workspace.id,
        source=SourceType.GITHUB,
        source_id="commit-123",
        content="Fixed the auth bug (updated)",
        author_id="user-123",
        timestamp=ts,
    )
    assert event2.id == event.id
    assert event2.content == "Fixed the auth bug (updated)"

    # Get unembedded
    unembedded = await event_repo.get_unembedded_events(session)
    assert any(e.id == event.id for e in unembedded)


async def test_ingestion_repository(session: AsyncSession):
    workspace = await workspace_repo.create(session, name="Ing Test", slug=f"ing-{uuid4()}")
    
    job = await ingestion_repo.create_job(
        session=session,
        workspace_id=workspace.id,
        source=SourceType.NOTION,
        source_config={"page_id": "123"},
        requested_by="Alice",
    )
    assert job.status == IngestionStatus.PENDING

    await ingestion_repo.mark_processing(session, job.id)
    
    job_updated = await ingestion_repo.get_by_id(session, job.id)
    assert job_updated.status == IngestionStatus.PROCESSING
    assert job_updated.started_at is not None

    await ingestion_repo.mark_completed(
        session=session,
        job_id=job.id,
        events_ingested=10,
        events_failed=2,
        processing_time_ms=5000,
    )

    job_done = await ingestion_repo.get_by_id(session, job.id)
    assert job_done.status == IngestionStatus.COMPLETED
    assert job_done.events_ingested == 10
    assert job_done.completed_at is not None


async def test_entity_registry_repository(session: AsyncSession):
    workspace = await workspace_repo.create(session, name="Ent Test", slug=f"ent-{uuid4()}")

    entity = await entity_registry_repo.register_entity(
        session=session,
        workspace_id=workspace.id,
        entity_type=EntityType.PERSON,
        canonical_name="Alice Chen",
    )
    assert entity.id is not None
    assert entity.source_event_count == 1

    # Register same again
    entity2 = await entity_registry_repo.register_entity(
        session=session,
        workspace_id=workspace.id,
        entity_type=EntityType.PERSON,
        canonical_name="Alice Chen",
    )
    assert entity2.id == entity.id
    assert entity2.source_event_count == 2
