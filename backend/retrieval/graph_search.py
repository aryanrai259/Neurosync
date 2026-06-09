# Purpose:      Graph search — extracts entity names from a query string,
#               traverses the Neo4j graph neighborhood, and returns events
#               associated with those entities, hydrated from PostgreSQL.
# Called By:    retrieval/hybrid.py
# Calls:        graph/queries.py (find_events_by_entity)
#               db/models/event.py (EventModel — hydration)
#               memory/entity_resolver.py (EntityResolver — for query entity extraction)
#               retrieval/schemas.py (RetrievedChunk)
# Dependencies: neo4j (async session), sqlalchemy (AsyncSession), python stdlib (logging)
# Test File:    tests/unit/retrieval/test_hybrid.py

import logging
from uuid import UUID

from neo4j import AsyncDriver
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models.event import EventModel
from backend.graph import queries as graph_queries
from backend.memory.entity_resolver import EntityResolver
from backend.models.event import NormalizedEvent
from backend.retrieval.schemas import RetrievedChunk

logger = logging.getLogger(__name__)


def _extract_query_entities(query: str) -> list[str]:
    """
    Extract entity canonical names from a free-text query string.
    Uses EntityResolver's seed-list and pattern matching tiers.
    Returns a list of canonical_name strings.
    """
    # Build a synthetic NormalizedEvent from the query string so we can
    # reuse EntityResolver without duplicating logic.
    from datetime import datetime, timezone
    from backend.models.enums import SourceType

    # Minimal synthetic event wrapping the query text
    try:
        import uuid
        synthetic = NormalizedEvent(
            id=uuid.uuid4(),
            source=SourceType.SLACK,
            workspace_id=uuid.uuid4(),
            source_id="query",
            content=query,
            author_id="query_user",
            timestamp=datetime.now(timezone.utc),
        )
        resolver = EntityResolver()
        refs = resolver.resolve(synthetic)
        return [ref.canonical_name for ref in refs]
    except Exception as exc:
        logger.warning("graph_search: entity extraction from query failed: %s", exc)
        return []


async def graph_search(
    session: AsyncSession,
    driver: AsyncDriver,
    workspace_id: UUID,
    query: str,
    k: int = 10,
) -> list[RetrievedChunk]:
    """
    Traverse the Neo4j graph for entities mentioned in the query and
    return the associated events, hydrated from PostgreSQL.

    Steps:
      1. Extract entity names from the query (seed-list + pattern matching).
      2. For each entity, find linked event_ids via Neo4j traversal.
      3. Deduplicate event_ids.
      4. Hydrate from PostgreSQL events table.
      5. Return RetrievedChunks with graph_score=1.0.

    Returns empty list if no graph entities match or graph is unavailable.
    """
    if not query or not query.strip():
        return []

    # Step 1: extract entities from query
    entity_names = _extract_query_entities(query)
    if not entity_names:
        logger.debug("graph_search: no entities extracted from query=%r", query[:40])
        return []

    # Step 2: find event_ids from graph
    seen_event_ids: set[str] = set()
    async with driver.session() as graph_session:
        for name in entity_names:
            try:
                event_ids = await graph_queries.find_events_by_entity(
                    graph_session, workspace_id, name
                )
                seen_event_ids.update(event_ids)
            except Exception as exc:
                logger.warning(
                    "graph_search: query failed for entity=%r: %s", name, exc
                )

    if not seen_event_ids:
        return []

    # Limit to k results
    top_event_ids = list(seen_event_ids)[:k]

    # Step 3: hydrate from Postgres
    from uuid import UUID as _UUID
    uuid_ids = []
    for eid in top_event_ids:
        try:
            uuid_ids.append(_UUID(eid))
        except ValueError:
            pass

    stmt = select(EventModel).where(EventModel.id.in_(uuid_ids))
    result = await session.execute(stmt)
    events = result.scalars().all()

    chunks: list[RetrievedChunk] = []
    for event in events:
        chunks.append(RetrievedChunk(
            event_id=event.id,
            content=event.content,
            title=event.title,
            source=event.source,
            timestamp=event.timestamp,
            author_id=event.author_id,
            url=event.url,
            vector_score=0.0,
            graph_score=1.0,
            combined_score=0.3,   # 0.7*0.0 + 0.3*1.0
        ))

    logger.debug(
        "graph_search: query=%r entities=%d event_ids=%d chunks=%d",
        query[:40], len(entity_names), len(seen_event_ids), len(chunks),
    )
    return chunks
