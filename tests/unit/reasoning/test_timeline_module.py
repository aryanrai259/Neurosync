"""Unit tests for backend/reasoning/timeline_module.py

Tests the timeline bucketing logic without any database dependency.
"""
import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from backend.reasoning.timeline_module import build_timeline, TimelineBucket, TimelineEvent


def make_event_dict(days_ago: int = 0, content: str = "Test event") -> dict:
    """Helper to build a minimal event dict."""
    ts = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return {
        "id": uuid4(),
        "timestamp": ts,
        "source": "slack",
        "raw_author": "alice",
        "raw_content": content,
        "entity_mentions": ["auth-service"],
    }


# ---------------------------------------------------------------------------
# Timeline bucket tests
# ---------------------------------------------------------------------------

def test_empty_events_returns_empty():
    """No events produce no buckets."""
    result = build_timeline([], granularity="daily")
    assert result == []


def test_single_event_produces_one_bucket():
    """One event produces exactly one bucket."""
    events = [make_event_dict(0)]
    buckets = build_timeline(events, granularity="daily")
    assert len(buckets) == 1
    assert len(buckets[0].events) == 1


def test_same_day_events_in_one_bucket():
    """Multiple events on the same day share a single bucket."""
    now = datetime.now(timezone.utc)
    events = [
        {"id": uuid4(), "timestamp": now, "source": "slack", "raw_author": "alice",
         "raw_content": "event 1", "entity_mentions": []},
        {"id": uuid4(), "timestamp": now - timedelta(hours=2), "source": "github",
         "raw_author": "bob", "raw_content": "event 2", "entity_mentions": []},
    ]
    buckets = build_timeline(events, granularity="daily")
    assert len(buckets) == 1
    assert len(buckets[0].events) == 2


def test_different_day_events_separate_buckets():
    """Events on different days produce separate buckets."""
    events = [
        make_event_dict(0),
        make_event_dict(1),
        make_event_dict(3),
    ]
    buckets = build_timeline(events, granularity="daily")
    assert len(buckets) == 3


def test_weekly_granularity_groups_same_week():
    """Events in the same ISO week are grouped together."""
    # Use two events 2 days apart but in the same week
    monday = datetime.now(timezone.utc) - timedelta(days=datetime.now().weekday())
    wednesday = monday + timedelta(days=2)
    events = [
        {"id": uuid4(), "timestamp": monday, "source": "slack", "raw_author": "alice",
         "raw_content": "Monday event", "entity_mentions": []},
        {"id": uuid4(), "timestamp": wednesday, "source": "github", "raw_author": "bob",
         "raw_content": "Wednesday event", "entity_mentions": []},
    ]
    buckets = build_timeline(events, granularity="weekly")
    assert len(buckets) == 1
    assert len(buckets[0].events) == 2


def test_monthly_granularity():
    """Events in the same month produce one bucket."""
    now = datetime.now(timezone.utc)
    events = [
        {"id": uuid4(), "timestamp": now.replace(day=1), "source": "slack",
         "raw_author": "alice", "raw_content": "Day 1", "entity_mentions": []},
        {"id": uuid4(), "timestamp": now.replace(day=min(now.day, 15)), "source": "github",
         "raw_author": "bob", "raw_content": "Mid month", "entity_mentions": []},
    ]
    buckets = build_timeline(events, granularity="monthly")
    assert len(buckets) == 1


def test_buckets_ordered_chronologically():
    """Buckets are returned in ascending chronological order."""
    events = [
        make_event_dict(3),
        make_event_dict(0),
        make_event_dict(7),
    ]
    buckets = build_timeline(events, granularity="daily")
    starts = [b.start for b in buckets]
    assert starts == sorted(starts)


def test_bucket_label_daily():
    """Daily bucket label is in YYYY-MM-DD format."""
    events = [make_event_dict(0)]
    buckets = build_timeline(events, granularity="daily")
    label = buckets[0].label
    # Should match YYYY-MM-DD
    assert len(label) == 10
    assert label[4] == "-"
    assert label[7] == "-"


def test_timeline_event_summary_truncated_to_200():
    """Event summary is truncated to 200 chars."""
    long_content = "x" * 500
    events = [make_event_dict(0, content=long_content)]
    buckets = build_timeline(events, granularity="daily")
    assert len(buckets[0].events[0].summary) <= 200


def test_to_dict_structure():
    """to_dict() returns expected keys."""
    events = [make_event_dict(0)]
    buckets = build_timeline(events, granularity="daily")
    d = buckets[0].to_dict()
    assert "label" in d
    assert "start" in d
    assert "end" in d
    assert "event_count" in d
    assert "events" in d
    assert d["event_count"] == 1
