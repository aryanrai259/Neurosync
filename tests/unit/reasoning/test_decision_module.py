"""Unit tests for backend/reasoning/decision_module.py

Tests the heuristic decision extraction logic without any database.
"""
import pytest
from uuid import uuid4

from backend.reasoning.decision_module import extract_decision_candidates
from backend.models.query import RetrievedChunk


def make_chunk(content: str, event_id=None) -> RetrievedChunk:
    """Helper to build a RetrievedChunk for testing."""
    from backend.models.enums import SourceType, RetrievalStrategy
    from datetime import datetime, timezone
    return RetrievedChunk(
        event_id=event_id or uuid4(),
        content=content,
        source=SourceType.SLACK,
        source_id=f"test-{uuid4().hex[:8]}",
        score=0.85,
        retrieval_method=RetrievalStrategy.HYBRID,
        timestamp=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# Extraction tests
# ---------------------------------------------------------------------------

def test_extracts_decision_from_decided_to():
    """'decided to' pattern is recognized."""
    chunk = make_chunk("The team decided to migrate to PostgreSQL for all storage.")
    result = extract_decision_candidates([chunk])
    assert len(result) == 1


def test_extracts_decision_from_approved():
    """'approved' pattern is recognized."""
    chunk = make_chunk("The proposal was approved by engineering leadership.")
    result = extract_decision_candidates([chunk])
    assert len(result) == 1


def test_no_decision_in_plain_text():
    """Non-decision text yields no candidates."""
    chunk = make_chunk("Auth service was deployed to production at 3pm.")
    result = extract_decision_candidates([chunk])
    assert len(result) == 0


def test_extracts_decided_by():
    """'decided by' attribution is extracted correctly."""
    chunk = make_chunk("We decided to use Redis for caching. Decided by the Platform Team.")
    result = extract_decision_candidates([chunk])
    assert len(result) == 1
    assert result[0]["decided_by"] is not None
    assert "Platform Team" in result[0]["decided_by"]


def test_deduplicates_same_event_id():
    """Same event_id only appears once even if multiple chunks share it."""
    shared_id = uuid4()
    chunks = [
        make_chunk("We decided to use PostgreSQL.", shared_id),
        make_chunk("We decided to use Redis.", shared_id),  # Same event_id
    ]
    result = extract_decision_candidates(chunks)
    assert len(result) == 1


def test_multiple_decisions_different_events():
    """Different events produce separate candidates."""
    chunks = [
        make_chunk("The team agreed to use TypeScript for all new services."),
        make_chunk("We decided to drop Python 2 support."),
        make_chunk("The proposal was approved: migrate to GKE."),
    ]
    result = extract_decision_candidates(chunks)
    assert len(result) == 3


def test_title_is_first_sentence():
    """Title is extracted as the first sentence."""
    chunk = make_chunk("We will adopt GraphQL for the new API. This was discussed on Monday.")
    result = extract_decision_candidates([chunk])
    assert len(result) == 1
    assert result[0]["title"] == "We will adopt GraphQL for the new API."


def test_source_event_id_is_set():
    """Source event ID matches the chunk's event_id."""
    event_id = uuid4()
    chunk = make_chunk("The team decided to rewrite in Go.", event_id)
    result = extract_decision_candidates([chunk])
    assert len(result) == 1
    assert result[0]["source_event_id"] == event_id


def test_empty_chunks_returns_empty():
    """Empty input returns empty list."""
    result = extract_decision_candidates([])
    assert result == []
