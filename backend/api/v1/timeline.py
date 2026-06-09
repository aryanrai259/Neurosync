# Purpose:      Timeline API endpoints — chronological event history for entities.
#               Returns time-bucketed event series for an entity or workspace.
# Called By:    backend/main.py (router)
# Calls:        reasoning/timeline_module.py, db/session.py
# Dependencies: fastapi, sqlalchemy
# Test File:    tests/integration/api/test_timeline_api.py

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_db_session
from backend.reasoning.timeline_module import get_entity_timeline

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/timeline", tags=["timeline"])


@router.get(
    "/{workspace_id}/entity/{entity_id}",
    summary="Get chronological event timeline for an entity",
    description=(
        "Returns a chronologically bucketed timeline of all events mentioning "
        "the specified entity. Supports daily, weekly, or monthly granularity."
    ),
)
async def get_timeline(
    workspace_id: UUID,
    entity_id: UUID,
    granularity: str = Query(
        default="daily",
        pattern="^(daily|weekly|monthly)$",
        description="Bucket granularity: daily, weekly, or monthly",
    ),
    days_back: int = Query(default=90, ge=1, le=365, description="Days of history to include"),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Returns timeline buckets for an entity.

    Each bucket contains:
    - label (e.g. "2026-01-15" for daily)
    - start / end timestamps
    - event_count
    - events (list of event summaries)
    """
    buckets = await get_entity_timeline(
        session=session,
        workspace_id=workspace_id,
        entity_id=entity_id,
        granularity=granularity,
        days_back=days_back,
    )

    total_events = sum(b.get("event_count", 0) for b in buckets)
    logger.info(
        "Timeline: workspace=%s entity=%s granularity=%s buckets=%d events=%d",
        workspace_id, entity_id, granularity, len(buckets), total_events,
    )

    return {
        "workspace_id": str(workspace_id),
        "entity_id": str(entity_id),
        "granularity": granularity,
        "days_back": days_back,
        "bucket_count": len(buckets),
        "total_events": total_events,
        "buckets": buckets,
    }


@router.get(
    "/{workspace_id}/entity/{entity_id}/summary",
    summary="Lightweight timeline summary (no event details)",
)
async def get_timeline_summary(
    workspace_id: UUID,
    entity_id: UUID,
    granularity: str = Query(default="weekly", pattern="^(daily|weekly|monthly)$"),
    days_back: int = Query(default=30, ge=1, le=365),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Returns timeline buckets without the full event list — faster for dashboards.
    Each bucket contains only: label, start, end, event_count.
    """
    buckets = await get_entity_timeline(
        session=session,
        workspace_id=workspace_id,
        entity_id=entity_id,
        granularity=granularity,
        days_back=days_back,
    )

    # Strip event details from response
    summary_buckets = [
        {
            "label": b["label"],
            "start": b["start"],
            "end": b["end"],
            "event_count": b["event_count"],
        }
        for b in buckets
    ]

    return {
        "workspace_id": str(workspace_id),
        "entity_id": str(entity_id),
        "granularity": granularity,
        "days_back": days_back,
        "total_events": sum(b["event_count"] for b in summary_buckets),
        "buckets": summary_buckets,
    }
