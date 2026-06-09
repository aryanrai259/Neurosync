# Purpose:      Neo4j schema setup — idempotent constraint and index creation.
#               Must be called once at application startup before any graph writes.
#               Safe to call multiple times (all statements use IF NOT EXISTS).
# Called By:    backend/main.py (startup lifespan event)
# Calls:        graph/client.py (get_driver)
# Dependencies: neo4j (official async driver)
# Test File:    tests/integration/graph/test_graph_schema.py

import logging

from neo4j import AsyncDriver

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Cypher DDL statements — node key constraints enforce uniqueness and
# create an implicit index. All are idempotent via IF NOT EXISTS.
# ---------------------------------------------------------------------------
_CONSTRAINTS: list[str] = [
    # Workspace: unique by workspace_id
    "CREATE CONSTRAINT unique_workspace IF NOT EXISTS "
    "FOR (w:Workspace) REQUIRE w.workspace_id IS UNIQUE",

    # Event: unique by event_id (UUID from PostgreSQL events.id)
    "CREATE CONSTRAINT unique_event IF NOT EXISTS "
    "FOR (e:Event) REQUIRE e.event_id IS UNIQUE",

    # Person: unique per workspace
    "CREATE CONSTRAINT unique_person IF NOT EXISTS "
    "FOR (p:Person) REQUIRE (p.workspace_id, p.canonical_name) IS UNIQUE",

    # Team: unique per workspace
    "CREATE CONSTRAINT unique_team IF NOT EXISTS "
    "FOR (t:Team) REQUIRE (t.workspace_id, t.canonical_name) IS UNIQUE",

    # Service: unique per workspace
    "CREATE CONSTRAINT unique_service IF NOT EXISTS "
    "FOR (s:Service) REQUIRE (s.workspace_id, s.canonical_name) IS UNIQUE",

    # Repository: unique per workspace
    "CREATE CONSTRAINT unique_repository IF NOT EXISTS "
    "FOR (r:Repository) REQUIRE (r.workspace_id, r.canonical_name) IS UNIQUE",

    # Ticket: unique per workspace
    "CREATE CONSTRAINT unique_ticket IF NOT EXISTS "
    "FOR (t:Ticket) REQUIRE (t.workspace_id, t.canonical_name) IS UNIQUE",

    # Document: unique per workspace
    "CREATE CONSTRAINT unique_document IF NOT EXISTS "
    "FOR (d:Document) REQUIRE (d.workspace_id, d.canonical_name) IS UNIQUE",
]


async def create_schema(driver: AsyncDriver) -> None:
    """
    Apply all constraints and indexes to the Neo4j graph.

    Safe to call on every startup — all statements are idempotent.
    Logs each statement so startup issues are easy to diagnose.

    Args:
        driver: The async Neo4j driver from graph/client.py.
    """
    async with driver.session() as session:
        for cypher in _CONSTRAINTS:
            try:
                await session.run(cypher)
                logger.debug("graph schema: applied: %s", cypher[:60])
            except Exception as exc:
                logger.error(
                    "graph schema: failed to apply constraint: %s — %s",
                    cypher[:60], exc,
                )
                raise

    logger.info("graph schema: all constraints applied (%d)", len(_CONSTRAINTS))
