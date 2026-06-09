# Purpose:      FastAPI application entrypoint for Company Brain backend.
#               Mounts all API routers and configures shared middleware (CORS, rate limiting).
#               Start with: uvicorn backend.main:app --reload
# Called By:    uvicorn (production), pytest (integration tests)
# Calls:        api/v1/ingest.py, api/v1/reasoning.py, api/v1/config.py,
#               api/v1/health.py, api/v1/workspaces.py, api/v1/jobs.py, api/v1/admin.py,
#               api/v1/auth.py, api/v1/decisions.py, api/v1/timeline.py
# Dependencies: fastapi, fastapi.middleware.cors, slowapi

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from backend.api.middleware.telemetry import RequestLatencyMiddleware
from backend.api.v1.admin import router as admin_router
from backend.api.v1.auth import router as auth_router
from backend.api.v1.config import router as config_router
from backend.api.v1.decisions import router as decisions_router
from backend.api.v1.health import router as health_router
from backend.api.v1.ingest import router as ingest_router
from backend.api.v1.jobs import router as jobs_router
from backend.api.v1.metrics import router as metrics_router
from backend.api.v1.reasoning import router as reasoning_router
from backend.api.v1.timeline import router as timeline_router
from backend.api.v1.workspaces import router as workspaces_router
from backend.core.rate_limiter import limiter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

app = FastAPI(
    title="Company Brain",
    description=(
        "Organizational intelligence platform. "
        "Ingests Slack, GitHub, and Jira events, builds a knowledge graph "
        "and vector memory, and answers natural language queries with grounded citations."
    ),
    version="0.7.0-dev",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ---------------------------------------------------------------------------
# Rate limiting state — slowapi reads limiter from app.state
# ---------------------------------------------------------------------------
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(RequestLatencyMiddleware)

# ---------------------------------------------------------------------------
# CORS — allow all origins in development; restrict in production via env var
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # Override with specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(ingest_router, prefix="/api/v1")
app.include_router(config_router)
app.include_router(reasoning_router)
app.include_router(health_router)
app.include_router(workspaces_router)
app.include_router(jobs_router)
app.include_router(admin_router)
app.include_router(auth_router)
app.include_router(decisions_router)
app.include_router(timeline_router)
app.include_router(metrics_router)


# ---------------------------------------------------------------------------
# Root health probe (liveness — no dependency checks)
# ---------------------------------------------------------------------------
@app.get("/health", tags=["meta"])
async def health() -> dict:
    """Liveness probe. Returns 200 if the server process is running. See /api/v1/health/deep for dependency checks."""
    return {"status": "ok", "version": app.version}
