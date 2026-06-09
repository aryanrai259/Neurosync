# Purpose:      Named Cypher read queries for graph retrieval.
#               Each function returns a list of event_ids linked to a query entity.
#               Used by retrieval/graph_search.py to hydrate results from Postgres.
#               All queries are workspace-scoped.
# Called By:    retrieval/graph_search.py
# Calls:        (neo4j session passed in — no driver import here)
# Dependencies: neo4j (async session), python stdlib (logging)
# Test File:    tests/integration/graph/test_graph_queries.py

import logging
from uuid import UUID

logger = logging.getLogger(__name__)


async def find_events_by_entity(
    session,
    workspace_id: UUID,
    canonical_name: str,
) -> list[str]:
    """
    Find all event_ids where a given entity was mentioned.

    Traverses AFFECTS, DISCUSSED_IN, REFERENCES, and AUTHORED edges
    from the entity node to Event nodes.

    Returns a list of event_id strings (UUIDs as strings).
    Returns empty list if entity not found.
    """
    result = await session.run(
        """
        MATCH (n {workspace_id: $workspace_id, canonical_name: $name})
        MATCH (n)-[:AFFECTS|DISCUSSED_IN|REFERENCES|AUTHORED]-(e:Event)
        RETURN DISTINCT e.event_id AS event_id
        LIMIT 50
        """,
        workspace_id=str(workspace_id),
        name=canonical_name,
    )
    records = await result.data()
    return [r["event_id"] for r in records if r["event_id"]]


async def find_neighborhood(
    session,
    workspace_id: UUID,
    canonical_name: str,
    depth: int = 2,
) -> list[dict]:
    """
    Return the 1–2 hop neighborhood of an entity node.
    Used for graph-aware context expansion in retrieval.

    Returns a list of dicts with keys: name, label, relationship, event_ids.
    """
    result = await session.run(
        """
        MATCH (start {workspace_id: $workspace_id, canonical_name: $name})
        MATCH (start)-[r*1..2]-(neighbor)
        WHERE neighbor.workspace_id = $workspace_id
        RETURN
            neighbor.canonical_name AS name,
            labels(neighbor)[0]     AS label,
            [rel IN r | type(rel)]  AS relationships
        LIMIT 30
        """,
        workspace_id=str(workspace_id),
        name=canonical_name,
    )
    records = await result.data()
    return records


async def find_service_owners(
    session,
    workspace_id: UUID,
    service_name: str,
) -> list[str]:
    """
    Find team names that own a given service.
    Returns list of team canonical_names.
    """
    result = await session.run(
        """
        MATCH (t:Team {workspace_id: $workspace_id})-[:OWNS]->(s:Service {workspace_id: $workspace_id, canonical_name: $service})
        RETURN t.canonical_name AS team_name
        """,
        workspace_id=str(workspace_id),
        service=service_name,
    )
    records = await result.data()
    return [r["team_name"] for r in records]
