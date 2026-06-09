"""Unit tests for backend/core/telemetry.py"""
import json
import logging
import pytest


class TestStructuredFormatter:
    def test_formats_as_valid_json(self):
        from backend.core.telemetry import StructuredFormatter
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test.logger", level=logging.INFO, pathname="", lineno=0,
            msg="test message", args=(), exc_info=None
        )
        output = formatter.format(record)
        parsed = json.loads(output)
        assert parsed["msg"] == "test message"
        assert parsed["level"] == "INFO"
        assert parsed["logger"] == "test.logger"
        assert parsed["service"] == "company-brain"
        assert "ts" in parsed

    def test_merges_extra_fields(self):
        from backend.core.telemetry import StructuredFormatter
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="trace", args=(), exc_info=None
        )
        record.query_id = "abc-123"
        record.retrieval_ms = 42
        output = formatter.format(record)
        parsed = json.loads(output)
        assert parsed["query_id"] == "abc-123"
        assert parsed["retrieval_ms"] == 42

    def test_non_serializable_extra_converted_to_str(self):
        from backend.core.telemetry import StructuredFormatter
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test", level=logging.WARNING, pathname="", lineno=0,
            msg="warn", args=(), exc_info=None
        )
        record.custom_obj = object()  # Not JSON serializable
        output = formatter.format(record)
        parsed = json.loads(output)
        assert "custom_obj" in parsed
        assert isinstance(parsed["custom_obj"], str)


class TestRequestTimer:
    def test_timer_measures_elapsed(self):
        import time
        from backend.core.telemetry import RequestTimer
        with RequestTimer() as timer:
            time.sleep(0.01)
        assert timer.elapsed_ms >= 10
        assert timer.elapsed_ms < 200  # Should be much less than 200ms

    def test_timer_starts_at_zero(self):
        from backend.core.telemetry import RequestTimer
        t = RequestTimer()
        assert t.elapsed_ms == 0


class TestSystemMetrics:
    def test_collect_returns_expected_keys(self):
        from backend.core.telemetry import collect_system_metrics
        metrics = collect_system_metrics()
        assert "ts" in metrics
        assert "service" in metrics
        assert "python_version" in metrics
        assert "gc" in metrics

    def test_gc_has_three_generations(self):
        from backend.core.telemetry import collect_system_metrics
        metrics = collect_system_metrics()
        assert "gen0_collections" in metrics["gc"]
        assert "gen1_collections" in metrics["gc"]
        assert "gen2_collections" in metrics["gc"]

    def test_service_name_is_company_brain(self):
        from backend.core.telemetry import collect_system_metrics
        metrics = collect_system_metrics()
        assert metrics["service"] == "company-brain"
