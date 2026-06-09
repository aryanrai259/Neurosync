# Purpose:      Neo4j driver lifecycle management.
#               Provides a singleton async driver connected to Neo4j.
#               All graph operations share this driver — never create drivers inline.
#               Call close_driver() on application shutdown.
# Called By:    graph/schema.py, graph/writer.py, graph/queries.py
# Calls:        core/config.py (neo4j_uri, neo4j_user, neo4j_password)
# Dependencies: neo4j (official async driver)
# Test File:    tests/integration/graph/test_graph_writer.py

import logging

from neo4j import AsyncDriver, AsyncGraphDatabase

from backend.core.config import get_settings

logger = logging.getLogger(__name__)

_driver: AsyncDriver | None = None


def get_driver() -> AsyncDriver:
    """
    Return the singleton Neo4j async driver, initializing it if needed.

    Thread-safe for reads. First call connects; subsequent calls return cached.
    Raises RuntimeError if connection configuration is missing.
    """
    global _driver
    if _driver is None:
        settings = get_settings()
        _driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
        logger.info("Neo4j driver initialized: %s", settings.neo4j_uri)
    return _driver


async def close_driver() -> None:
    """
    Close the Neo4j driver gracefully.
    Call this in the FastAPI lifespan shutdown event.
    """
    global _driver
    if _driver is not None:
        await _driver.close()
        _driver = None
        logger.info("Neo4j driver closed.")


async def verify_connectivity() -> bool:
    """
    Test that the Neo4j server is reachable.
    Returns True on success, False on failure. Never raises.
    """
    try:
        driver = get_driver()
        await driver.verify_connectivity()
        return True
    except Exception as exc:
        logger.warning("Neo4j connectivity check failed: %s", exc)
        return False
