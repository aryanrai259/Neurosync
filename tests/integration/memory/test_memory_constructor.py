# Purpose:      Integration tests for memory/memory_constructor.py
#               Requires running PostgreSQL (docker-compose up -d)
#               Tests that MemoryConstructor builds a MemoryObject and persists
#               it correctly to the memory_objects table.
# Run with:     pytest tests/integration/memory/test_memory_constructor.py -v

import pytest
import pytest_asyncio
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.core.config import get_settings
from backend.db.models.memory_object import MemoryObjectModel
from backend.db.repositories.memory_repo import MemoryObjectRepository, memory_object_repo
from backend.db.repositories.workspace_repo import workspace_repo
from backend.db.session import get_engine
from backend.memory.entity_resolver import EntityResolver
from backend.memory.memory_constructor import MemoryConstructor
from backend.memory.relationship_extractor import RelationshipExtractor
from backend.models.enums import SourceType
from backend.models.event import NormalizedEvent

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
    slug = f"mem-constructor-test-{uuid4()}"
    ws = await workspace_repo.create(session, name="Memory Test Workspace", slug=slug)
    return ws


@pytest_asyncio.fixture
def constructor():
    return MemoryConstructor(
        resolver=EntityResolver(
            service_names=["auth-service", "payment-gateway"],
            team_names=["platform-team"],
        ),
        extractor=RelationshipExtractor(),
        repo=memory_object_repo,
    )


def _make_normalized_event(workspace_id, **kwargs) -> NormalizedEvent:
    defaults = dict(
        source=SourceType.SLACK,
        workspace_id=workspace_id,
        source_id=f"test-{uuid4()}",
        content="auth-service is down, platform-team is investigating",
        author_id="alice",
        timestamp=datetime.now(timezone.utc),
    )
    return NormalizedEvent(**{**defaults, **kwargs})


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

async def test_construct_returns_memory_object(session, workspace, constructor):
    """construct() must return a MemoryObject with correct event_id."""
    event = _make_normalized_event(workspace.id)
    event_id = uuid4()

    mo = await constructor.construct(event, event_id, session)

    assert mo.event_id == event_id
    assert mo.workspace_id == workspace.id
    assert mo.content == event.content


async def test_construct_persists_to_db(session, workspace, constructor):
    """construct() must write a row to memory_objects."""
    event = _make_normalized_event(workspace.id)
    event_id = uuid4()

    await constructor.construct(event, event_id, session)

    stmt = select(MemoryObjectModel).where(MemoryObjectModel.event_id == event_id)
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()

    assert row is not None
    assert row.event_id == event_id
    assert row.workspace_id == workspace.id


async def test_construct_extracts_service_entities(session, workspace, constructor):
    """Service names in content should appear as entities in the MemoryObject."""
    event = _make_normalized_event(
        workspace.id,
        content="auth-service failed during deployment"
    )
    event_id = uuid4()

    mo = await constructor.construct(event, event_id, session)

    entity_names = [e.canonical_name for e in mo.entities]
    assert "auth-service" in entity_names


async def test_construct_entities_stored_as_json(session, workspace, constructor):
    """Entities must be serialised as JSON in memory_objects.entities."""
    event = _make_normalized_event(workspace.id)
    event_id = uuid4()

    mo = await constructor.construct(event, event_id, session)

    row = await memory_object_repo.get_by_event_id(session, event_id)
    assert row is not None
    assert isinstance(row.entities, list)


async def test_construct_relationships_stored_as_json(session, workspace, constructor):
    """Relationships must be serialised as JSON in memory_objects.relationships."""
    event = _make_normalized_event(workspace.id)
    event_id = uuid4()

    await constructor.construct(event, event_id, session)

    row = await memory_object_repo.get_by_event_id(session, event_id)
    assert isinstance(row.relationships, list)


async def test_construct_idempotency_raises_on_duplicate_event_id(session, workspace, constructor):
    """Calling construct() twice with the same event_id must raise (write-once table)."""
    from sqlalchemy.exc import IntegrityError

    event = _make_normalized_event(workspace.id)
    event_id = uuid4()

    await constructor.construct(event, event_id, session)

    with pytest.raises(Exception):  # IntegrityError from unique constraint
        await constructor.construct(event, event_id, session)


async def test_delete_by_event_id_enables_replay(session, workspace, constructor):
    """delete_by_event_id() followed by construct() should succeed (replay pattern)."""
    event = _make_normalized_event(workspace.id)
    event_id = uuid4()

    await constructor.construct(event, event_id, session)

    deleted = await memory_object_repo.delete_by_event_id(session, event_id)
    assert deleted is True

    # Re-insert after delete (replay)
    await constructor.construct(event, event_id, session)

    row = await memory_object_repo.get_by_event_id(session, event_id)
    assert row is not None


async def test_construct_empty_entities_when_no_match(session, workspace, constructor):
    """No-match content should produce empty entities list."""
    no_match_constructor = MemoryConstructor(
        resolver=EntityResolver(service_names=[], team_names=[]),
        extractor=RelationshipExtractor(),
        repo=memory_object_repo,
    )
    event = _make_normalized_event(
        workspace.id,
        content="nothing special here",
        author_id="bot",   # bot is excluded from person extraction
    )
    event_id = uuid4()

    mo = await no_match_constructor.construct(event, event_id, session)
    assert mo.entities == []
    assert mo.relationships == []
