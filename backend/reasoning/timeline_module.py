# Purpose:      Timeline module — retrieves chronologically ordered events for an entity
#               and structures them into timeline buckets (daily/weekly/monthly).
#               Provides the data layer for GET /api/v1/timeline/{entity_id}.
# Called By:    api/v1/timeline.py
# Calls:        db/repositories/timeline_repo.py
# Dependencies: sqlalchemy, datetime
# Test File:    tests/unit/reasoning/test_timeline_module.py

import logging
from datetime import datetime, timezone, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.repositories.timeline_repo import timeline_repo

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Timeline data structures
# ---------------------------------------------------------------------------

class TimelineEvent:
    """A single event entry within a timeline."""


    def __init__(
        self,
        event_id: UUID,
        timestamp: datetime,
        source: str,
        author: str | None,
        summary: str,
        entity_mentions: list[str],
    ) -> None:
        self.event_id = event_id
        self.timestamp = timestamp
        self.source = source
        self.author = author
        self.summary = summary
        self.entity_mentions = entity_mentions

    def to_dict(self) -> dict:
        return {
            "event_id": str(self.event_id),
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "author": self.author,
            "summary": self.summary,
            "entity_mentions": self.entity_mentions,
        }


class TimelineBucket:
    """A date-bounded group of events (e.g. a single day or week)."""

    def __init__(self, label: str, start: datetime, end: datetime) -> None:
        self.label = label
        self.start = start
        self.end = end
        self.events: list[TimelineEvent] = []

    def to_dict(self) -> dict:
        return {
            "label": self.label,
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "event_count": len(self.events),
            "events": [e.to_dict() for e in self.events],
        }


# ---------------------------------------------------------------------------
# Timeline construction
# ---------------------------------------------------------------------------

def _bucket_label(dt: datetime, granularity: str) -> str:
    if granularity == "daily":
        return dt.strftime("%Y-%m-%d")
    if granularity == "weekly":
        # ISO week
        year, week, _ = dt.isocalendar()
        return f"{year}-W{week:02d}"
    return dt.strftime("%Y-%m")  # monthly


def build_timeline(
    events: list[dict],
    granularity: str = "daily",
) -> list[TimelineBucket]:
    """
    Bucket a list of event dicts into TimelineBucket groups.

    Args:
        events:      List of event dicts from timeline_repo.get_events_for_entity.
        granularity: 'daily' | 'weekly' | 'monthly'

    Returns:
        List of TimelineBucket ordered by start date ascending.
    """
    if not events:
        return []

    buckets: dict[str, TimelineBucket] = {}

    for ev in events:
        ts: datetime = ev.get("timestamp") or datetime.now(timezone.utc)
        label = _bucket_label(ts, granularity)

        if label not in buckets:
            # Compute bucket start/end from the label
            if granularity == "daily":
                start = datetime(ts.year, ts.month, ts.day, tzinfo=ts.tzinfo)
                end = start + timedelta(days=1)
            elif granularity == "weekly":
                start = ts - timedelta(days=ts.weekday())
                start = datetime(start.year, start.month, start.day, tzinfo=ts.tzinfo)
                end = start + timedelta(weeks=1)
            else:
                import calendar
                start = datetime(ts.year, ts.month, 1, tzinfo=ts.tzinfo)
                # First day of next month
                if ts.month == 12:
                    end = datetime(ts.year + 1, 1, 1, tzinfo=ts.tzinfo)
                else:
                    end = datetime(ts.year, ts.month + 1, 1, tzinfo=ts.tzinfo)

            buckets[label] = TimelineBucket(label=label, start=start, end=end)

        bucket = buckets[label]
        timeline_event = TimelineEvent(
            event_id=ev["id"],
            timestamp=ts,
            source=str(ev.get("source", "unknown")),
            author=ev.get("raw_author"),
            summary=(ev.get("raw_content") or "")[:200],
            entity_mentions=ev.get("entity_mentions", []),
        )
        bucket.events.append(timeline_event)

    # Sort buckets chronologically
    sorted_buckets = sorted(buckets.values(), key=lambda b: b.start)
    return sorted_buckets


async def get_entity_timeline(
    session: AsyncSession,
    workspace_id: UUID,
    entity_id: UUID,
    granularity: str = "daily",
    days_back: int = 90,
) -> list[dict]:
    """
    Retrieve and bucket events for an entity.

    Args:
        session:      Active async DB session.
        workspace_id: Workspace scope.
        entity_id:    Entity UUID to build timeline for.
        granularity:  'daily' | 'weekly' | 'monthly'.
        days_back:    How many days of history to include.

    Returns:
        List of bucket dicts (serializable).
    """
    since = datetime.now(timezone.utc) - timedelta(days=days_back)

    events = await timeline_repo.get_events_for_entity(
        session=session,
        workspace_id=workspace_id,
        entity_id=entity_id,
        since=since,
    )

    buckets = build_timeline(events, granularity=granularity)

    logger.info(
        "Timeline for entity %s: %d events in %d buckets (%s granularity)",
        entity_id, sum(len(b.events) for b in buckets), len(buckets), granularity,
    )

    return [b.to_dict() for b in buckets]
