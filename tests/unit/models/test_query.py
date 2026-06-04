# Purpose:      Unit tests for models/query.py
#               Tests: QueryFilters, QueryRequest, RetrievedChunk, QueryResponse
#               All validator branches, all boundaries, all required/optional fields
# Dependencies: pytest, pydantic v2
# Run with:     pytest tests/unit/models/test_query.py -v --cov=backend

import pytest
from datetime import datetime, timezone, timedelta
from uuid import UUID, uuid4

from pydantic import ValidationError

from backend.models.enums import RetrievalStrategy, SourceType
from backend.models.query import (
    QueryFilters,
    QueryRequest,
    QueryResponse,
    RetrievedChunk,
)


# ─── Shared helpers ───────────────────────────────────────────────────────────

UTC = timezone.utc
NOW = datetime.now(UTC)
PAST = datetime(2024, 1, 1, tzinfo=UTC)
FUTURE = datetime(2025, 1, 1, tzinfo=UTC)


def _make_chunk(**kwargs) -> RetrievedChunk:
    defaults = dict(
        event_id=uuid4(),
        content="Auth service moved to Redis for session storage.",
        source=SourceType.SLACK,
        source_id="slack-ts-123456",
        timestamp=NOW,
        score=0.85,
        retrieval_method=RetrievalStrategy.HYBRID,
    )
    return RetrievedChunk(**{**defaults, **kwargs})


def _make_request(**kwargs) -> QueryRequest:
    defaults = dict(
        query="Why did we move auth to Redis?",
        workspace_id=uuid4(),
    )
    return QueryRequest(**{**defaults, **kwargs})


def _make_response(**kwargs) -> QueryResponse:
    defaults = dict(
        answer="The auth service moved to Redis in Q3 2024 for scalability.",
        confidence=0.9,
        session_id="session-abc-123",
        retrieval_count=15,
        processing_time_ms=342,
    )
    return QueryResponse(**{**defaults, **kwargs})


# ─── QueryFilters ─────────────────────────────────────────────────────────────


class TestQueryFilters:
    def test_all_fields_none_by_default(self):
        f = QueryFilters()
        assert f.sources is None
        assert f.time_from is None
        assert f.time_to is None
        assert f.author_ids is None

    def test_sources_can_be_set(self):
        f = QueryFilters(sources=[SourceType.SLACK, SourceType.GITHUB])
        assert SourceType.SLACK in f.sources

    def test_author_ids_can_be_set(self):
        f = QueryFilters(author_ids=["U123", "U456"])
        assert f.author_ids == ["U123", "U456"]

    def test_valid_time_range_accepted(self):
        f = QueryFilters(time_from=PAST, time_to=FUTURE)
        assert f.time_from == PAST
        assert f.time_to == FUTURE

    def test_time_from_equal_to_time_to_raises(self):
        with pytest.raises(ValidationError, match="before time_to"):
            QueryFilters(time_from=PAST, time_to=PAST)

    def test_time_from_after_time_to_raises(self):
        with pytest.raises(ValidationError, match="before time_to"):
            QueryFilters(time_from=FUTURE, time_to=PAST)

    def test_only_time_from_set_is_valid(self):
        f = QueryFilters(time_from=PAST)
        assert f.time_from == PAST
        assert f.time_to is None

    def test_only_time_to_set_is_valid(self):
        f = QueryFilters(time_to=FUTURE)
        assert f.time_to == FUTURE
        assert f.time_from is None

    def test_naive_time_from_raises(self):
        with pytest.raises(ValidationError, match="timezone-aware"):
            QueryFilters(time_from=datetime(2024, 1, 1))

    def test_naive_time_to_raises(self):
        with pytest.raises(ValidationError, match="timezone-aware"):
            QueryFilters(time_to=datetime(2025, 1, 1))

    def test_filters_is_frozen(self):
        f = QueryFilters()
        with pytest.raises(ValidationError):
            f.sources = [SourceType.SLACK]  # type: ignore


# ─── QueryRequest ─────────────────────────────────────────────────────────────


class TestQueryRequest:
    def test_missing_query_raises(self):
        with pytest.raises(ValidationError):
            QueryRequest(workspace_id=uuid4())

    def test_missing_workspace_id_raises(self):
        with pytest.raises(ValidationError):
            QueryRequest(query="test query")

    def test_default_strategy_is_hybrid(self):
        assert _make_request().strategy == RetrievalStrategy.HYBRID

    def test_default_max_results_is_10(self):
        assert _make_request().max_results == 10

    def test_default_min_confidence_is_0_7(self):
        assert _make_request().min_confidence == 0.7

    def test_default_session_id_is_none(self):
        assert _make_request().session_id is None

    def test_default_filters_is_none(self):
        assert _make_request().filters is None

    def test_whitespace_only_query_raises(self):
        with pytest.raises(ValidationError, match="whitespace-only"):
            _make_request(query="   ")

    def test_empty_query_raises(self):
        with pytest.raises(ValidationError):
            _make_request(query="")

    def test_tab_only_query_raises(self):
        with pytest.raises(ValidationError):
            _make_request(query="\t\t")

    def test_max_results_below_minimum_raises(self):
        with pytest.raises(ValidationError):
            _make_request(max_results=0)

    def test_max_results_above_maximum_raises(self):
        with pytest.raises(ValidationError):
            _make_request(max_results=51)

    def test_max_results_at_boundary_1_valid(self):
        assert _make_request(max_results=1).max_results == 1

    def test_max_results_at_boundary_50_valid(self):
        assert _make_request(max_results=50).max_results == 50

    def test_min_confidence_below_0_raises(self):
        with pytest.raises(ValidationError):
            _make_request(min_confidence=-0.01)

    def test_min_confidence_above_1_raises(self):
        with pytest.raises(ValidationError):
            _make_request(min_confidence=1.01)

    def test_min_confidence_at_0_valid(self):
        assert _make_request(min_confidence=0.0).min_confidence == 0.0

    def test_min_confidence_at_1_valid(self):
        assert _make_request(min_confidence=1.0).min_confidence == 1.0

    def test_session_id_can_be_set(self):
        req = _make_request(session_id="sess-xyz-789")
        assert req.session_id == "sess-xyz-789"

    def test_filters_can_be_set(self):
        f = QueryFilters(sources=[SourceType.GITHUB])
        req = _make_request(filters=f)
        assert req.filters.sources == [SourceType.GITHUB]

    def test_request_is_frozen(self):
        req = _make_request()
        with pytest.raises(ValidationError):
            req.query = "modified"  # type: ignore

    @pytest.mark.parametrize("strategy", list(RetrievalStrategy))
    def test_all_strategies_accepted(self, strategy: RetrievalStrategy):
        req = _make_request(strategy=strategy)
        assert req.strategy == strategy


# ─── RetrievedChunk ───────────────────────────────────────────────────────────


class TestRetrievedChunk:
    def test_missing_event_id_raises(self):
        with pytest.raises(ValidationError):
            RetrievedChunk(
                content="text", source=SourceType.SLACK,
                source_id="x", timestamp=NOW, score=0.5,
                retrieval_method=RetrievalStrategy.VECTOR,
            )

    def test_missing_score_raises(self):
        with pytest.raises(ValidationError):
            RetrievedChunk(
                event_id=uuid4(), content="text",
                source=SourceType.SLACK, source_id="x",
                timestamp=NOW, retrieval_method=RetrievalStrategy.VECTOR,
            )

    def test_missing_timestamp_raises(self):
        with pytest.raises(ValidationError):
            RetrievedChunk(
                event_id=uuid4(), content="text",
                source=SourceType.SLACK, source_id="x",
                score=0.5, retrieval_method=RetrievalStrategy.VECTOR,
            )

    def test_optional_fields_are_none_by_default(self):
        chunk = _make_chunk()
        assert chunk.title is None
        assert chunk.url is None
        assert chunk.author_name is None

    def test_content_whitespace_only_raises(self):
        with pytest.raises(ValidationError, match="whitespace-only"):
            _make_chunk(content="   ")

    def test_empty_content_raises(self):
        with pytest.raises(ValidationError):
            _make_chunk(content="")

    def test_score_at_0_valid(self):
        assert _make_chunk(score=0.0).score == 0.0

    def test_score_at_1_valid(self):
        assert _make_chunk(score=1.0).score == 1.0

    def test_score_below_0_raises(self):
        with pytest.raises(ValidationError):
            _make_chunk(score=-0.01)

    def test_score_above_1_raises(self):
        with pytest.raises(ValidationError):
            _make_chunk(score=1.01)

    def test_naive_timestamp_raises(self):
        with pytest.raises(ValidationError, match="timezone-aware"):
            _make_chunk(timestamp=datetime(2024, 1, 1))

    def test_aware_timestamp_accepted(self):
        ts = datetime(2024, 6, 1, tzinfo=UTC)
        assert _make_chunk(timestamp=ts).timestamp == ts

    def test_non_utc_timezone_accepted(self):
        tz_ist = timezone(timedelta(hours=5, minutes=30))
        ts = datetime(2024, 6, 1, 12, 0, tzinfo=tz_ist)
        chunk = _make_chunk(timestamp=ts)
        assert chunk.timestamp.tzinfo == tz_ist

    def test_optional_fields_can_be_set(self):
        chunk = _make_chunk(
            title="Fix auth timeout",
            url="https://github.com/acme/api/pull/234",
            author_name="Alice Chen",
        )
        assert chunk.title == "Fix auth timeout"
        assert chunk.url == "https://github.com/acme/api/pull/234"
        assert chunk.author_name == "Alice Chen"

    def test_chunk_is_frozen(self):
        chunk = _make_chunk()
        with pytest.raises(ValidationError):
            chunk.score = 0.5  # type: ignore

    def test_event_id_is_uuid(self):
        event_id = uuid4()
        chunk = _make_chunk(event_id=event_id)
        assert chunk.event_id == event_id

    @pytest.mark.parametrize("method", list(RetrievalStrategy))
    def test_all_retrieval_methods_accepted(self, method: RetrievalStrategy):
        chunk = _make_chunk(retrieval_method=method)
        assert chunk.retrieval_method == method

    @pytest.mark.parametrize("source", list(SourceType))
    def test_all_source_types_accepted(self, source: SourceType):
        chunk = _make_chunk(source=source)
        assert chunk.source == source


# ─── QueryResponse ────────────────────────────────────────────────────────────


class TestQueryResponse:
    def test_missing_answer_raises(self):
        with pytest.raises(ValidationError):
            QueryResponse(
                confidence=0.9, session_id="s1",
                retrieval_count=5, processing_time_ms=100,
            )

    def test_missing_session_id_raises(self):
        with pytest.raises(ValidationError):
            QueryResponse(
                answer="answer", confidence=0.9,
                retrieval_count=5, processing_time_ms=100,
            )

    def test_query_id_auto_generated(self):
        resp = _make_response()
        assert isinstance(resp.query_id, UUID)

    def test_each_response_gets_unique_query_id(self):
        r1 = _make_response()
        r2 = _make_response()
        assert r1.query_id != r2.query_id

    def test_sources_empty_by_default(self):
        assert _make_response().sources == []

    def test_sources_can_contain_chunks(self):
        chunks = [_make_chunk(), _make_chunk()]
        resp = _make_response(sources=chunks)
        assert len(resp.sources) == 2

    def test_answer_whitespace_only_raises(self):
        with pytest.raises(ValidationError, match="whitespace-only"):
            _make_response(answer="   ")

    def test_empty_answer_raises(self):
        with pytest.raises(ValidationError):
            _make_response(answer="")

    def test_confidence_at_0_valid(self):
        assert _make_response(confidence=0.0).confidence == 0.0

    def test_confidence_at_1_valid(self):
        assert _make_response(confidence=1.0).confidence == 1.0

    def test_confidence_below_0_raises(self):
        with pytest.raises(ValidationError):
            _make_response(confidence=-0.01)

    def test_confidence_above_1_raises(self):
        with pytest.raises(ValidationError):
            _make_response(confidence=1.01)

    def test_processing_time_ms_zero_valid(self):
        assert _make_response(processing_time_ms=0).processing_time_ms == 0

    def test_processing_time_ms_negative_raises(self):
        with pytest.raises(ValidationError):
            _make_response(processing_time_ms=-1)

    def test_retrieval_count_zero_valid(self):
        assert _make_response(retrieval_count=0).retrieval_count == 0

    def test_retrieval_count_negative_raises(self):
        with pytest.raises(ValidationError):
            _make_response(retrieval_count=-1)

    def test_session_id_is_stored(self):
        resp = _make_response(session_id="sess-abc-789")
        assert resp.session_id == "sess-abc-789"

    def test_response_is_frozen(self):
        resp = _make_response()
        with pytest.raises(ValidationError):
            resp.answer = "modified"  # type: ignore


# ─── RetrievalStrategy enum ───────────────────────────────────────────────────


class TestRetrievalStrategyEnum:
    def test_all_expected_values_exist(self):
        values = {e.value for e in RetrievalStrategy}
        assert values == {"vector", "graph", "hybrid"}

    def test_strategy_is_string(self):
        assert isinstance(RetrievalStrategy.HYBRID, str)
        assert RetrievalStrategy.HYBRID == "hybrid"
