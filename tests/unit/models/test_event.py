# Purpose:      Unit tests for models/event.py — NormalizedEvent
# Tests:        Field defaults, required fields, validator branches (all paths),
#               immutability, deduplication fields, metadata flexibility
# Dependencies: pytest, pydantic v2
# Run with:     pytest tests/unit/models/test_event.py -v --cov=backend/models/event

import pytest
from datetime import datetime, timezone, timedelta
from uuid import UUID, uuid4

from pydantic import ValidationError

from backend.models.enums import EmbeddingStatus, SourceType
from backend.models.event import NormalizedEvent


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _make(**kwargs) -> NormalizedEvent:
    """Build a valid NormalizedEvent with sensible defaults for any omitted field."""
    defaults = dict(
        source=SourceType.SLACK,
        workspace_id=uuid4(),
        source_id="slack-msg-ts-1234567890.123456",
        content="Alice pushed a fix for the auth timeout bug.",
        author_id="U12345678",
        timestamp=datetime.now(timezone.utc),
    )
    return NormalizedEvent(**{**defaults, **kwargs})


# ─── Required fields ──────────────────────────────────────────────────────────


class TestRequiredFields:
    def test_missing_source_raises(self):
        with pytest.raises(ValidationError):
            NormalizedEvent(
                workspace_id=uuid4(),
                source_id="x",
                content="content",
                author_id="u1",
                timestamp=datetime.now(timezone.utc),
            )

    def test_missing_workspace_id_raises(self):
        with pytest.raises(ValidationError):
            NormalizedEvent(
                source=SourceType.GITHUB,
                source_id="x",
                content="content",
                author_id="u1",
                timestamp=datetime.now(timezone.utc),
            )

    def test_missing_source_id_raises(self):
        with pytest.raises(ValidationError):
            NormalizedEvent(
                source=SourceType.SLACK,
                workspace_id=uuid4(),
                content="content",
                author_id="u1",
                timestamp=datetime.now(timezone.utc),
            )

    def test_missing_content_raises(self):
        with pytest.raises(ValidationError):
            NormalizedEvent(
                source=SourceType.SLACK,
                workspace_id=uuid4(),
                source_id="x",
                author_id="u1",
                timestamp=datetime.now(timezone.utc),
            )

    def test_missing_author_id_raises(self):
        with pytest.raises(ValidationError):
            NormalizedEvent(
                source=SourceType.SLACK,
                workspace_id=uuid4(),
                source_id="x",
                content="content",
                timestamp=datetime.now(timezone.utc),
            )

    def test_missing_timestamp_raises(self):
        with pytest.raises(ValidationError):
            NormalizedEvent(
                source=SourceType.SLACK,
                workspace_id=uuid4(),
                source_id="x",
                content="content",
                author_id="u1",
            )


# ─── Default values ───────────────────────────────────────────────────────────


class TestDefaults:
    def test_id_is_uuid(self):
        event = _make()
        assert isinstance(event.id, UUID)

    def test_each_event_gets_unique_id(self):
        e1 = _make()
        e2 = _make()
        assert e1.id != e2.id

    def test_title_is_none_by_default(self):
        assert _make().title is None

    def test_author_name_is_none_by_default(self):
        assert _make().author_name is None

    def test_url_is_none_by_default(self):
        assert _make().url is None

    def test_metadata_is_empty_dict_by_default(self):
        assert _make().metadata == {}

    def test_embedding_status_is_pending_by_default(self):
        assert _make().embedding_status == EmbeddingStatus.PENDING

    def test_created_at_is_utc(self):
        event = _make()
        assert event.created_at.tzinfo == timezone.utc

    def test_created_at_is_auto_set(self):
        event = _make()
        assert isinstance(event.created_at, datetime)


# ─── Immutability ─────────────────────────────────────────────────────────────


class TestImmutability:
    def test_event_is_frozen(self):
        event = _make()
        with pytest.raises(ValidationError):
            event.content = "modified"  # type: ignore

    def test_embedding_status_cannot_be_mutated(self):
        event = _make()
        with pytest.raises(ValidationError):
            event.embedding_status = EmbeddingStatus.EMBEDDED  # type: ignore


# ─── content validator ────────────────────────────────────────────────────────


class TestContentValidator:
    def test_valid_content_is_accepted(self):
        event = _make(content="Valid content string.")
        assert event.content == "Valid content string."

    def test_whitespace_only_content_raises(self):
        with pytest.raises(ValidationError, match="whitespace-only"):
            _make(content="   ")

    def test_tab_only_content_raises(self):
        with pytest.raises(ValidationError):
            _make(content="\t\t\t")

    def test_newline_only_content_raises(self):
        with pytest.raises(ValidationError):
            _make(content="\n\n")

    def test_empty_content_raises(self):
        with pytest.raises(ValidationError):
            _make(content="")

    def test_content_with_surrounding_whitespace_is_accepted(self):
        # Content with surrounding whitespace is fine — only pure whitespace is rejected
        event = _make(content="  valid content  ")
        assert event.content == "  valid content  "


# ─── timestamp validator ──────────────────────────────────────────────────────


class TestTimestampValidator:
    def test_aware_timestamp_is_accepted(self):
        ts = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
        event = _make(timestamp=ts)
        assert event.timestamp == ts

    def test_naive_timestamp_raises(self):
        naive = datetime(2024, 6, 1, 12, 0, 0)  # no tzinfo
        with pytest.raises(ValidationError, match="timezone-aware"):
            _make(timestamp=naive)

    def test_non_utc_aware_timestamp_is_accepted(self):
        # We accept any timezone-aware datetime, not just UTC
        tz_india = timezone(timedelta(hours=5, minutes=30))
        ts = datetime(2024, 6, 1, 17, 30, 0, tzinfo=tz_india)
        event = _make(timestamp=ts)
        assert event.timestamp.tzinfo == tz_india

    def test_naive_created_at_raises(self):
        naive = datetime(2024, 6, 1, 12, 0, 0)
        with pytest.raises(ValidationError, match="timezone-aware"):
            _make(created_at=naive)


# ─── Optional fields ──────────────────────────────────────────────────────────


class TestOptionalFields:
    def test_title_can_be_set(self):
        event = _make(title="Fix auth timeout bug")
        assert event.title == "Fix auth timeout bug"

    def test_author_name_can_be_set(self):
        event = _make(author_name="Alice Chen")
        assert event.author_name == "Alice Chen"

    def test_url_can_be_set(self):
        event = _make(url="https://github.com/acme/api/pull/234")
        assert event.url == "https://github.com/acme/api/pull/234"

    def test_embedding_status_can_be_set(self):
        event = _make(embedding_status=EmbeddingStatus.EMBEDDED)
        assert event.embedding_status == EmbeddingStatus.EMBEDDED

    def test_metadata_can_hold_arbitrary_data(self):
        meta = {"thread_id": "T12345", "reaction_count": 3, "is_reply": True}
        event = _make(metadata=meta)
        assert event.metadata["thread_id"] == "T12345"
        assert event.metadata["reaction_count"] == 3

    def test_metadata_can_be_nested(self):
        meta = {"pr": {"number": 234, "labels": ["bug", "auth"]}}
        event = _make(metadata=meta)
        assert event.metadata["pr"]["labels"] == ["bug", "auth"]


# ─── source_id deduplication key ─────────────────────────────────────────────


class TestSourceId:
    def test_source_id_is_stored(self):
        event = _make(source_id="PROJ-1234")
        assert event.source_id == "PROJ-1234"

    def test_empty_source_id_raises(self):
        with pytest.raises(ValidationError):
            _make(source_id="")

    def test_two_events_same_source_id_different_objects(self):
        e1 = _make(source_id="same-id")
        e2 = _make(source_id="same-id")
        assert e1.source_id == e2.source_id
        assert e1.id != e2.id  # different internal IDs


# ─── All source types ─────────────────────────────────────────────────────────


class TestAllSourceTypes:
    @pytest.mark.parametrize("source", list(SourceType))
    def test_all_source_types_accepted(self, source: SourceType):
        event = _make(source=source)
        assert event.source == source
