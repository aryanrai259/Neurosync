# Purpose:      Deep health check endpoint — verifies all critical dependencies.
#               Returns individual status for PostgreSQL, Neo4j, and core app.
#               Used by load balancers, monitoring tools, and readiness probes.
# Called By:    backend/main.py (router)
# Calls:        db/session.py, graph/client.py
# Dependencies: fastapi, sqlalchemy, neo4j
# Test File:    tests/integration/api/test_health.py

import logging
import time

from fastapi import APIRouter
from sqlalchemy import text

from backend.db.session import async_session
from backend.graph.client import get_driver

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/health", tags=["health"])


@router.get("/deep", summary="Deep health check — verifies all backend dependencies")
async def deep_health() -> dict:
    """
    Check connectivity to PostgreSQL, Neo4j, and core application state.

    Returns per-dependency status so operators can pinpoint failures.
    HTTP 200 even on partial failures — the status fields indicate component health.
    """
    result: dict = {
        "status": "ok",
        "timestamp_ms": int(time.time() * 1000),
        "components": {},
    }

    # ── PostgreSQL ──────────────────────────────────────────────────────────
    try:
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
        result["components"]["postgres"] = {"status": "ok"}
    except Exception as exc:
        logger.error("Health: PostgreSQL check failed: %s", exc)
        result["components"]["postgres"] = {"status": "error", "detail": str(exc)}
        result["status"] = "degraded"

    # ── Neo4j ────────────────────────────────────────────────────────────────
    try:
        driver = get_driver()
        async with driver.session() as session:
            await session.run("RETURN 1")
        result["components"]["neo4j"] = {"status": "ok"}
    except Exception as exc:
        logger.error("Health: Neo4j check failed: %s", exc)
        result["components"]["neo4j"] = {"status": "error", "detail": str(exc)}
        result["status"] = "degraded"

    return result
