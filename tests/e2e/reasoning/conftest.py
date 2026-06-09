# tests/e2e/reasoning/conftest.py
# Module-scoped fixtures for E2E reasoning tests.
# The E2E tests use loop_scope="module", meaning all tests share one event loop.
# When this module ends, the loop closes, poisoning any singleton connections
# created on it. This conftest disposes the engine so subsequent test modules
# get fresh connections.

import pytest_asyncio


@pytest_asyncio.fixture(autouse=True, scope="module", loop_scope="module")
async def _cleanup_singletons_after_e2e():
    """Dispose engine and reset Neo4j driver after E2E module completes."""
    yield

    # Dispose the global engine so its pool drops stale connections
    from backend.db.session import engine
    await engine.dispose()

    # Reset the Neo4j driver singleton so it gets recreated on a fresh loop
    from backend.graph import client as graph_client
    if graph_client._driver is not None:
        try:
            await graph_client._driver.close()
        except Exception:
            pass
        graph_client._driver = None
