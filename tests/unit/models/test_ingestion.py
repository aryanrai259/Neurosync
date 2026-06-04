# Purpose:      Unit tests for models/ingestion.py
#               Tests: IngestionRequest, IngestionResult
# Dependencies: pytest, pydantic v2
# Run with:     pytest tests/unit/models/test_ingestion.py -v --cov=backend

import pytest
from datetime import datetime, timezone, timedelta
from uuid import UUID, uuid4

from pydantic import ValidationError

from backend.models.enums import IngestionStatus, SourceType
from backend.models.ingestion import IngestionRequest, IngestionResult

UTC = timezone.utc
NOW = datetime.now(UTC)


# ─── IngestionRequest ─────────────────────────────────────────────────────────

class TestIngestionRequest:
    def _make(self, **kwargs) -> IngestionRequest:
        defaults = dict(
            workspace_id=uuid4(),
            source=SourceType.SLACK,
            requested_by="user-abc-123",
        )
        return IngestionRequest(**{**defaults, **kwargs})

    def test_missing_workspace_id_raises(self):
        with pytest.raises(ValidationError):
            IngestionRequest(source=SourceType.SLACK, requested_by="u1")

    def test_missing_source_raises(self):
        with pytest.raises(ValidationError):
            IngestionRequest(workspace_id=uuid4(), requested_by="u1")

    def test_missing_requested_by_raises(self):
        with pytest.raises(ValidationError):
            IngestionRequest(workspace_id=uuid4(), source=SourceType.SLACK)

    def test_id_is_uuid(self):
        assert isinstance(self._make().id, UUID)

    def test_each_request_gets_unique_id(self):
        r1 = self._make()
        r2 = self._make()
        assert r1.id != r2.id

    def test_source_config_empty_by_default(self):
        assert self._make().source_config == {}

    def test_created_at_is_utc(self):
        assert self._make().created_at.tzinfo == UTC

    def test_whitespace_only_requested_by_raises(self):
        with pytest.raises(ValidationError, match="whitespace-only"):
            self._make(requested_by="   ")

    def test_empty_requested_by_raises(self):
        with pytest.raises(ValidationError):
            self._make(requested_by="")

    def test_naive_created_at_raises(self):
        with pytest.raises(ValidationError, match="timezone-aware"):
            self._make(created_at=datetime(2024, 1, 1))

    def test_source_config_can_hold_arbitrary_data(self):
        config = {"channel_ids": ["C123", "C456"], "since": "2024-01-01"}
        req = self._make(source_config=config)
        assert req.source_config["channel_ids"] == ["C123", "C456"]

    def test_source_config_can_be_nested(self):
        config = {"auth": {"token": "xoxb-...", "workspace": "T123"}}
        req = self._make(source_config=config)
        assert req.source_config["auth"]["workspace"] == "T123"

    def test_request_is_frozen(self):
        req = self._make()
        with pytest.raises(ValidationError):
            req.requested_by = "other"  # type: ignore

    @pytest.mark.parametrize("source", list(SourceType))
    def test_all_source_types_accepted(self, source: SourceType):
        req = self._make(source=source)
        assert req.source == source

    def test_non_utc_timezone_accepted(self):
        tz_ist = timezone(timedelta(hours=5, minutes=30))
        ts = datetime(2024, 6, 1, 12, 0, tzinfo=tz_ist)
        req = self._make(created_at=ts)
        assert req.created_at.tzinfo == tz_ist


# ─── IngestionResult ──────────────────────────────────────────────────────────

class TestIngestionResult:
    def _make(self, **kwargs) -> IngestionResult:
        defaults = dict(
            request_id=uuid4(),
            workspace_id=uuid4(),
            source=SourceType.GITHUB,
            status=IngestionStatus.COMPLETED,
            started_at=NOW,
        )
        return IngestionResult(**{**defaults, **kwargs})

    def test_missing_request_id_raises(self):
        with pytest.raises(ValidationError):
            IngestionResult(
                workspace_id=uuid4(),
                source=SourceType.SLACK,
                status=IngestionStatus.COMPLETED,
                started_at=NOW,
            )

    def test_missing_workspace_id_raises(self):
        with pytest.raises(ValidationError):
            IngestionResult(
                request_id=uuid4(),
                source=SourceType.SLACK,
                status=IngestionStatus.COMPLETED,
                started_at=NOW,
            )

    def test_missing_started_at_raises(self):
        with pytest.raises(ValidationError):
            IngestionResult(
                request_id=uuid4(),
                workspace_id=uuid4(),
                source=SourceType.SLACK,
                status=IngestionStatus.COMPLETED,
            )

    def test_events_ingested_zero_by_default(self):
        assert self._make().events_ingested == 0

    def test_events_failed_zero_by_default(self):
        assert self._make().events_failed == 0

    def test_error_message_none_by_default(self):
        assert self._make().error_message is None

    def test_completed_at_none_by_default(self):
        assert self._make().completed_at is None

    def test_processing_time_ms_none_by_default(self):
        assert self._make().processing_time_ms is None

    def test_events_ingested_negative_raises(self):
        with pytest.raises(ValidationError):
            self._make(events_ingested=-1)

    def test_events_failed_negative_raises(self):
        with pytest.raises(ValidationError):
            self._make(events_failed=-1)

    def test_processing_time_ms_negative_raises(self):
        with pytest.raises(ValidationError):
            self._make(processing_time_ms=-1)

    def test_processing_time_ms_zero_valid(self):
        assert self._make(processing_time_ms=0).processing_time_ms == 0

    def test_naive_started_at_raises(self):
        with pytest.raises(ValidationError, match="timezone-aware"):
            self._make(started_at=datetime(2024, 1, 1))

    def test_naive_completed_at_raises(self):
        with pytest.raises(ValidationError, match="timezone-aware"):
            self._make(completed_at=datetime(2024, 1, 1))

    def test_aware_completed_at_accepted(self):
        ts = datetime(2024, 6, 1, tzinfo=UTC)
        result = self._make(completed_at=ts)
        assert result.completed_at == ts

    def test_error_message_can_be_set(self):
        result = self._make(
            status=IngestionStatus.FAILED,
            error_message="Rate limit exceeded by Slack API",
        )
        assert result.error_message == "Rate limit exceeded by Slack API"

    def test_result_is_frozen(self):
        result = self._make()
        with pytest.raises(ValidationError):
            result.status = IngestionStatus.FAILED  # type: ignore

    def test_successful_result_shape(self):
        result = self._make(
            status=IngestionStatus.COMPLETED,
            events_ingested=142,
            events_failed=3,
            completed_at=NOW,
            processing_time_ms=4231,
        )
        assert result.events_ingested == 142
        assert result.events_failed == 3
        assert result.processing_time_ms == 4231

    @pytest.mark.parametrize("status", list(IngestionStatus))
    def test_all_statuses_accepted(self, status: IngestionStatus):
        result = self._make(status=status)
        assert result.status == status

    @pytest.mark.parametrize("source", list(SourceType))
    def test_all_source_types_accepted(self, source: SourceType):
        result = self._make(source=source)
        assert result.source == source


# ─── IngestionStatus enum ─────────────────────────────────────────────────────

class TestIngestionStatusEnum:
    def test_all_expected_values_exist(self):
        values = {e.value for e in IngestionStatus}
        assert values == {"pending", "processing", "completed", "failed"}

    def test_status_is_string(self):
        assert isinstance(IngestionStatus.COMPLETED, str)
        assert IngestionStatus.COMPLETED == "completed"
