# tests/conftest.py
# Root conftest for the test suite.
# Provides session-scoped cleanup of the global engine and Neo4j driver singletons
# to prevent "event loop is closed" errors when tests run across different event loops.

import pytest


@pytest.fixture(autouse=True, scope="session")
def _reset_singletons_at_end(request):
    """
    After the entire test session, dispose the global engine and close the Neo4j driver.
    This prevents stale connections from leaking between test runs.
    """
    yield

    # Synchronously dispose — the event loop is dead at this point, so we
    # reset the module-level references to None so the next import creates
    # fresh connections.
    import backend.db.session as db_session_mod
    import backend.graph.client as graph_client_mod

    # Reset engine to None — forces re-creation on next import
    try:
        db_session_mod.engine.sync_engine.dispose()
    except Exception:
        pass

    # Reset Neo4j driver singleton
    graph_client_mod._driver = None
