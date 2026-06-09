# Purpose:      Integration tests for graph/writer.py, graph/schema.py, graph/queries.py
#               Requires running Neo4j (docker-compose up -d)
#               Tests that nodes and edges are correctly upserted into Neo4j
#               from a MemoryObject.
# Run with:     pytest tests/integration/graph/test_graph_writer.py -v

import pytest
import pytest_asyncio
from datetime import datetime, timezone
from uuid import uuid4

from backend.graph.client import get_driver, close_driver
from backend.graph.schema import create_schema
from backend.graph.writer import GraphWriter
from backend.graph import queries as graph_queries
from backend.memory.memory_object import EntityRef, MemoryObject, RelationshipRef
from backend.models.enums import EntityType, SourceType

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def driver():
    """Create a fresh Neo4j driver for each test. Avoids singleton poisoning."""
    from neo4j import AsyncGraphDatabase
    from backend.core.config import get_settings
    settings = get_settings()
    d = AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )
    await d.verify_connectivity()
    await create_schema(d)
    yield d
    await d.close()


@pytest_asyncio.fixture
def writer(driver):
    return GraphWriter(driver=driver)


def _make_memory_object(workspace_id=None, **kwargs) -> MemoryObject:
    wid = workspace_id or uuid4()
    eid = uuid4()
    return MemoryObject(
        event_id=eid,
        workspace_id=wid,
        source=SourceType.GITHUB,
        content="auth-service deployment fix by alice",
        author_id="alice",
        timestamp=datetime.now(timezone.utc),
        entities=[
            EntityRef(
                canonical_name="alice",
                entity_type=EntityType.PERSON,
                confidence=1.0,
                extraction_source="structured_author_id",
            ),
            EntityRef(
                canonical_name="auth-service",
                entity_type=EntityType.SERVICE,
                confidence=1.0,
                extraction_source="seed_list_service",
            ),
        ],
        relationships=[
            RelationshipRef(
                subject=EntityRef(
                    canonical_name="alice",
                    entity_type=EntityType.PERSON,
                    confidence=1.0,
                    extraction_source="structured_author_id",
                ),
                predicate="AUTHORED",
                object=EntityRef(
                    canonical_name=str(eid),
                    entity_type=EntityType.DOCUMENT,
                    confidence=1.0,
                    extraction_source="event_identity",
                ),
                confidence=1.0,
                extraction_source="rule_authored_structured",
            ),
        ],
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Schema Tests
# ---------------------------------------------------------------------------

async def test_schema_creates_constraints_idempotently(driver):
    """Calling create_schema twice must not raise."""
    await create_schema(driver)  # Second call — should be idempotent


# ---------------------------------------------------------------------------
# Writer Tests
# ---------------------------------------------------------------------------

async def test_write_creates_event_node(writer, driver):
    """write() must create an Event node in Neo4j."""
    mo = _make_memory_object()
    await writer.write(mo)

    async with driver.session() as session:
        result = await session.run(
            "MATCH (e:Event {event_id: $event_id}) RETURN e",
            event_id=str(mo.event_id),
        )
        records = await result.data()

    assert len(records) == 1


async def test_write_creates_person_node(writer, driver):
    """write() must create a Person node for alice."""
    mo = _make_memory_object()
    wid = str(mo.workspace_id)
    await writer.write(mo)

    async with driver.session() as session:
        result = await session.run(
            "MATCH (p:Person {workspace_id: $wid, canonical_name: 'alice'}) RETURN p",
            wid=wid,
        )
        records = await result.data()

    assert len(records) >= 1


async def test_write_creates_service_node(writer, driver):
    """write() must create a Service node for auth-service."""
    mo = _make_memory_object()
    wid = str(mo.workspace_id)
    await writer.write(mo)

    async with driver.session() as session:
        result = await session.run(
            "MATCH (s:Service {workspace_id: $wid, canonical_name: 'auth-service'}) RETURN s",
            wid=wid,
        )
        records = await result.data()

    assert len(records) >= 1


async def test_write_is_idempotent(writer, driver):
    """Calling write() twice with the same MemoryObject must not create duplicates."""
    mo = _make_memory_object()
    await writer.write(mo)
    await writer.write(mo)

    async with driver.session() as session:
        result = await session.run(
            "MATCH (e:Event {event_id: $event_id}) RETURN count(e) as cnt",
            event_id=str(mo.event_id),
        )
        records = await result.data()

    assert records[0]["cnt"] == 1


async def test_write_empty_memory_object(writer, driver):
    """write() with no entities/relationships must create only the Event node."""
    mo = MemoryObject(
        event_id=uuid4(),
        workspace_id=uuid4(),
        source=SourceType.SLACK,
        content="a quiet event",
        author_id="bot",
        timestamp=datetime.now(timezone.utc),
        entities=[],
        relationships=[],
    )
    # Must not raise
    await writer.write(mo)

    async with driver.session() as session:
        result = await session.run(
            "MATCH (e:Event {event_id: $event_id}) RETURN e",
            event_id=str(mo.event_id),
        )
        records = await result.data()

    assert len(records) == 1


# ---------------------------------------------------------------------------
# Query Tests
# ---------------------------------------------------------------------------

async def test_find_events_by_entity_returns_event_ids(writer, driver):
    """find_events_by_entity should return event_ids for events mentioning a service."""
    mo = _make_memory_object()
    wid = mo.workspace_id

    # Add AFFECTS relationship for graph traversal to work
    from backend.memory.memory_object import RelationshipRef, EntityRef
    service_ref = EntityRef(
        canonical_name="auth-service",
        entity_type=EntityType.SERVICE,
        confidence=1.0,
        extraction_source="seed_list_service",
    )
    event_ref = EntityRef(
        canonical_name=str(mo.event_id),
        entity_type=EntityType.DOCUMENT,
        confidence=1.0,
        extraction_source="event_identity",
    )
    rel = RelationshipRef(
        subject=event_ref,
        predicate="AFFECTS",
        object=service_ref,
        confidence=1.0,
        extraction_source="rule_affects_service_mention",
    )
    mo_with_affects = mo.model_copy(update={"relationships": [*mo.relationships, rel]})
    await writer.write(mo_with_affects)

    async with driver.session() as session:
        event_ids = await graph_queries.find_events_by_entity(
            session, wid, "auth-service"
        )

    assert str(mo.event_id) in event_ids


async def test_find_service_owners_returns_teams(writer, driver):
    """find_service_owners should return team names owning a service."""
    workspace_id = uuid4()
    team_ref = EntityRef(
        canonical_name="platform-team",
        entity_type=EntityType.TEAM,
        confidence=1.0,
        extraction_source="seed_list_team",
    )
    service_ref = EntityRef(
        canonical_name="query-svc",
        entity_type=EntityType.SERVICE,
        confidence=1.0,
        extraction_source="seed_list_service",
    )
    owns_rel = RelationshipRef(
        subject=team_ref,
        predicate="OWNS",
        object=service_ref,
        confidence=0.6,
        extraction_source="rule_owns_cooccurrence",
    )
    mo = MemoryObject(
        event_id=uuid4(),
        workspace_id=workspace_id,
        source=SourceType.SLACK,
        content="platform-team owns query-svc",
        author_id="bot",
        timestamp=datetime.now(timezone.utc),
        entities=[team_ref, service_ref],
        relationships=[owns_rel],
    )
    writer_inst = GraphWriter(driver=driver)
    await writer_inst.write(mo)

    async with driver.session() as session:
        owners = await graph_queries.find_service_owners(
            session, workspace_id, "query-svc"
        )

    assert "platform-team" in owners
