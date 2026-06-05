# Purpose:      FastAPI application entrypoint for Company Brain backend.
#               Mounts all API routers and configures shared middleware.
#               Start with: uvicorn backend.main:app --reload
# Called By:    uvicorn (production), pytest (integration tests)
# Calls:        api/v1/ingest.py (router)
# Dependencies: fastapi

import logging

from fastapi import FastAPI

from backend.api.v1.ingest import router as ingest_router

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="Company Brain",
    description="Organizational intelligence platform. Ingests Slack, GitHub, Jira events and answers natural language queries.",
    version="0.4.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(ingest_router, prefix="/api/v1")


@app.get("/health", tags=["meta"])
async def health() -> dict:
    """Liveness probe. Returns 200 if the server is running."""
    return {"status": "ok", "version": app.version}
