"""Unit tests for the evaluation framework (scripts/evaluate.py).

Tests the evaluation logic in isolation — no live backend required.
"""
import pytest
import sys
import importlib.util
from pathlib import Path

# Load evaluate.py as a module using its absolute path
_EVALUATE_PY = Path(__file__).parent.parent.parent.parent / "scripts" / "evaluate.py"
spec = importlib.util.spec_from_file_location("evaluate", _EVALUATE_PY)
_evaluate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_evaluate)

_meets_confidence = _evaluate._meets_confidence
_check_keywords = _evaluate._check_keywords
evaluate_query = _evaluate.evaluate_query
_CONFIDENCE_ORDER = _evaluate._CONFIDENCE_ORDER


class TestConfidenceOrdering:
    def test_low_meets_low(self):
        assert _meets_confidence("LOW", "LOW") is True

    def test_medium_meets_low(self):
        assert _meets_confidence("MEDIUM", "LOW") is True

    def test_high_meets_medium(self):
        assert _meets_confidence("HIGH", "MEDIUM") is True

    def test_low_does_not_meet_medium(self):
        assert _meets_confidence("LOW", "MEDIUM") is False

    def test_low_does_not_meet_high(self):
        assert _meets_confidence("LOW", "HIGH") is False

    def test_medium_does_not_meet_high(self):
        assert _meets_confidence("MEDIUM", "HIGH") is False

    def test_high_meets_high(self):
        assert _meets_confidence("HIGH", "HIGH") is True


class TestKeywordCheck:
    def test_all_keywords_present(self):
        ok, missing = _check_keywords(
            "We decided to use PostgreSQL for storage",
            ["postgresql", "storage"],
        )
        assert ok is True
        assert missing == []

    def test_case_insensitive(self):
        ok, missing = _check_keywords(
            "We chose POSTGRESQL",
            ["postgresql"],
        )
        assert ok is True

    def test_missing_keyword(self):
        ok, missing = _check_keywords(
            "We use Redis",
            ["postgresql", "redis"],
        )
        assert ok is False
        assert "postgresql" in missing
        assert "redis" not in missing

    def test_empty_keywords(self):
        ok, missing = _check_keywords("anything", [])
        assert ok is True
        assert missing == []


class TestEvaluateQuery:
    def _make_golden(
        self,
        id="gq-test",
        category="general",
        query="test query",
        expected_keywords=None,
        required_sources=None,
        min_confidence="LOW",
        expected_citations_min=0,
    ):
        return {
            "id": id,
            "category": category,
            "query": query,
            "expected_keywords": expected_keywords or [],
            "required_sources": required_sources or [],
            "min_confidence": min_confidence,
            "expected_citations_min": expected_citations_min,
            "notes": "",
        }

    def _make_result(
        self,
        answer="The answer is here",
        strategy="HYBRID",
        confidence="MEDIUM",
        citation_count=2,
        execution_ms=500,
    ):
        return {
            "query_id": "test-id",
            "answer": answer,
            "strategy": strategy,
            "confidence": confidence,
            "citations": ["abc"] * citation_count,
            "citation_count": citation_count,
            "execution_ms": execution_ms,
        }

    def test_passing_query(self):
        golden = self._make_golden(
            expected_keywords=["answer"],
            min_confidence="LOW",
            expected_citations_min=1,
        )
        result = self._make_result(answer="The answer is here", confidence="MEDIUM", citation_count=2)
        eval_result = evaluate_query(golden, result)
        assert eval_result["pass"] is True

    def test_fails_on_low_confidence(self):
        golden = self._make_golden(min_confidence="HIGH")
        result = self._make_result(confidence="LOW")
        eval_result = evaluate_query(golden, result)
        assert eval_result["pass"] is False
        assert eval_result["criteria"]["confidence"]["pass"] is False

    def test_fails_on_insufficient_citations(self):
        golden = self._make_golden(expected_citations_min=3)
        result = self._make_result(citation_count=1)
        eval_result = evaluate_query(golden, result)
        assert eval_result["pass"] is False
        assert eval_result["criteria"]["citations"]["pass"] is False

    def test_fails_on_latency_exceeded(self):
        golden = self._make_golden()
        result = self._make_result(execution_ms=35_000)  # > 30s cap
        eval_result = evaluate_query(golden, result)
        assert eval_result["pass"] is False
        assert eval_result["criteria"]["latency"]["pass"] is False

    def test_missing_keywords_does_not_hard_fail(self):
        """Keyword check is soft — warn but don't fail the overall pass."""
        golden = self._make_golden(
            expected_keywords=["missing-keyword"],
            min_confidence="LOW",
            expected_citations_min=0,
        )
        result = self._make_result(answer="Completely unrelated answer", citation_count=0)
        eval_result = evaluate_query(golden, result)
        # hard_pass = confidence(ok) AND citations(ok) AND latency(ok)
        assert eval_result["pass"] is True  # keywords are soft
        assert eval_result["criteria"]["keywords"]["pass"] is False  # but flagged

    def test_empty_answer_with_no_citations_passes_if_low_required(self):
        """No supporting evidence found → still passes if min requirements are LOW/0."""
        golden = self._make_golden(min_confidence="LOW", expected_citations_min=0)
        result = self._make_result(
            answer="No supporting evidence found.",
            confidence="LOW",
            citation_count=0,
        )
        eval_result = evaluate_query(golden, result)
        assert eval_result["pass"] is True


class TestGoldenQueriesFile:
    def test_golden_queries_file_exists(self):
        path = Path(__file__).parent.parent.parent.parent / "data" / "eval" / "golden_queries.json"
        assert path.exists(), f"golden_queries.json not found at {path}"

    def test_golden_queries_structure(self):
        import json
        path = Path(__file__).parent.parent.parent.parent / "data" / "eval" / "golden_queries.json"
        with open(path) as f:
            data = json.load(f)
        assert "queries" in data
        assert len(data["queries"]) >= 10, "Need at least 10 golden queries"
        for q in data["queries"]:
            assert "id" in q
            assert "query" in q
            assert "min_confidence" in q
            assert q["min_confidence"] in ("LOW", "MEDIUM", "HIGH")

    def test_golden_query_ids_unique(self):
        import json
        path = Path(__file__).parent.parent.parent.parent / "data" / "eval" / "golden_queries.json"
        with open(path) as f:
            data = json.load(f)
        ids = [q["id"] for q in data["queries"]]
        assert len(ids) == len(set(ids)), "Duplicate query IDs found"
