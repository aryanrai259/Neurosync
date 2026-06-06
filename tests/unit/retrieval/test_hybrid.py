# Purpose:      Unit tests for retrieval/hybrid.py
# Tests:        Merge, deduplication, score combination, top-K ordering.
#               Pure function tests — no DB, no network.
# Run with:     pytest tests/unit/retrieval/test_hybrid.py -v

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from backend.models.enums import SourceType
from backend.retrieval.hybrid import GRAPH_WEIGHT, VECTOR_WEIGHT, _compute_combined_score, merge
from backend.retrieval.schemas import RetrievedChunk


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _make_chunk(
    event_id: UUID | None = None,
    vector_score: float = 0.0,
    graph_score: float = 0.0,
    combined_score: float = 0.0,
    **kwargs,
) -> RetrievedChunk:
    return RetrievedChunk(
        event_id=event_id or uuid4(),
        content="some event content",
        source=SourceType.SLACK,
        timestamp=datetime.now(timezone.utc),
        author_id="alice",
        vector_score=vector_score,
        graph_score=graph_score,
        combined_score=combined_score,
        **kwargs,
    )


# ─── _compute_combined_score ──────────────────────────────────────────────────

class TestComputeCombinedScore:
    def test_vector_only_score(self):
        score = _compute_combined_score(1.0, 0.0)
        assert score == round(VECTOR_WEIGHT * 1.0, 4)

    def test_graph_only_score(self):
        score = _compute_combined_score(0.0, 1.0)
        assert score == round(GRAPH_WEIGHT * 1.0, 4)

    def test_both_max_score(self):
        score = _compute_combined_score(1.0, 1.0)
        assert score == 1.0

    def test_zero_both_is_zero(self):
        assert _compute_combined_score(0.0, 0.0) == 0.0

    def test_clamped_to_1(self):
        assert _compute_combined_score(1.0, 1.0) <= 1.0

    def test_clamped_to_0(self):
        assert _compute_combined_score(0.0, 0.0) >= 0.0

    def test_partial_scores_combined(self):
        score = _compute_combined_score(0.8, 0.6)
        expected = round(0.7 * 0.8 + 0.3 * 0.6, 4)
        assert score == expected


# ─── merge ────────────────────────────────────────────────────────────────────

class TestMerge:
    def test_empty_both_returns_empty(self):
        result = merge([], [])
        assert result == []

    def test_vector_only_results_returned(self):
        chunk = _make_chunk(vector_score=0.9, combined_score=0.63)
        result = merge([chunk], [])
        assert len(result) == 1

    def test_graph_only_results_returned(self):
        chunk = _make_chunk(graph_score=1.0, combined_score=0.3)
        result = merge([], [chunk])
        assert len(result) == 1

    def test_deduplication_same_event_id(self):
        event_id = uuid4()
        v = _make_chunk(event_id=event_id, vector_score=0.9)
        g = _make_chunk(event_id=event_id, graph_score=1.0)
        result = merge([v], [g])
        assert len(result) == 1

    def test_dedup_chunk_has_both_scores(self):
        event_id = uuid4()
        v = _make_chunk(event_id=event_id, vector_score=0.9)
        g = _make_chunk(event_id=event_id, graph_score=1.0)
        result = merge([v], [g])
        assert result[0].graph_score == 1.0
        assert result[0].vector_score == 0.9

    def test_combined_score_recomputed_on_dedup(self):
        event_id = uuid4()
        v = _make_chunk(event_id=event_id, vector_score=0.8)
        g = _make_chunk(event_id=event_id, graph_score=1.0)
        result = merge([v], [g])
        expected = round(0.7 * 0.8 + 0.3 * 1.0, 4)
        assert result[0].combined_score == expected

    def test_sorted_by_combined_score_descending(self):
        chunks = [
            _make_chunk(vector_score=0.3),
            _make_chunk(vector_score=0.9),
            _make_chunk(vector_score=0.6),
        ]
        result = merge(chunks, [])
        scores = [c.combined_score for c in result]
        assert scores == sorted(scores, reverse=True)

    def test_top_k_respected(self):
        chunks = [_make_chunk(vector_score=round((i % 10) / 10, 1)) for i in range(20)]
        result = merge(chunks, [], k=5)
        assert len(result) <= 5

    def test_two_unique_events_both_returned(self):
        v1 = _make_chunk(vector_score=0.9)
        v2 = _make_chunk(vector_score=0.7)
        result = merge([v1, v2], [])
        assert len(result) == 2

    def test_graph_chunk_score_is_0_3_when_no_vector(self):
        g = _make_chunk(graph_score=1.0)
        result = merge([], [g])
        assert result[0].combined_score == round(0.3 * 1.0, 4)
