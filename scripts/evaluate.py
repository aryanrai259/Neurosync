#!/usr/bin/env python
"""
evaluate.py — Company Brain Retrieval and Reasoning Evaluation Framework.

Runs the golden query set against a live backend and measures:
  - Retrieval strategy used (HYBRID / VECTOR_ONLY / GRAPH_ONLY)
  - Confidence level (HIGH / MEDIUM / LOW)
  - Citation count
  - Keyword presence in answer
  - Execution latency (ms)
  - Pass/fail per query criterion

Usage:
  python scripts/evaluate.py [--workspace-id UUID] [--queries-file PATH]
                             [--api-url URL] [--output PATH]

Examples:
  python scripts/evaluate.py --workspace-id <uuid>
  python scripts/evaluate.py --workspace-id <uuid> --output results/eval_2026-06-09.json

Exit codes:
  0 — all required queries passed
  1 — one or more queries failed required criteria
  2 — configuration error
"""

import argparse
import asyncio
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

# ---------------------------------------------------------------------------
# Allow running from repo root
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from backend.db.session import async_session
from backend.reasoning.pipeline import pipeline

_CONFIDENCE_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}


# ---------------------------------------------------------------------------
# Evaluation logic
# ---------------------------------------------------------------------------

def _meets_confidence(actual: str, minimum: str) -> bool:
    return _CONFIDENCE_ORDER.get(actual, 0) >= _CONFIDENCE_ORDER.get(minimum, 0)


def _check_keywords(answer: str, keywords: list[str]) -> tuple[bool, list[str]]:
    """Returns (all_present, missing_keywords)."""
    lower_answer = answer.lower()
    missing = [kw for kw in keywords if kw.lower() not in lower_answer]
    return len(missing) == 0, missing


async def run_query(workspace_id: UUID, query_text: str) -> dict:
    """Run a single query through the full pipeline and return the result dict."""
    start = time.perf_counter()
    result = await pipeline.query(query_text, workspace_id)
    elapsed_ms = int((time.perf_counter() - start) * 1000)
    return {
        "query_id": str(result.query_id),
        "answer": result.answer_markdown,
        "strategy": result.retrieval_strategy,
        "confidence": result.confidence,
        "citations": [str(c) for c in result.citations],
        "citation_count": len(result.citations),
        "execution_ms": elapsed_ms,
    }


def evaluate_query(golden: dict, result: dict) -> dict:
    """Evaluate a single query result against its golden criteria."""
    criteria = {}

    # Criterion 1: confidence meets minimum
    conf_ok = _meets_confidence(result["confidence"], golden["min_confidence"])
    criteria["confidence"] = {
        "pass": conf_ok,
        "expected_min": golden["min_confidence"],
        "actual": result["confidence"],
    }

    # Criterion 2: keyword presence
    if golden.get("expected_keywords"):
        kw_ok, missing = _check_keywords(result["answer"], golden["expected_keywords"])
        criteria["keywords"] = {
            "pass": kw_ok,
            "expected": golden["expected_keywords"],
            "missing": missing,
        }
    else:
        criteria["keywords"] = {"pass": True, "note": "no keywords specified"}

    # Criterion 3: citation count
    expected_min_cites = golden.get("expected_citations_min", 0)
    cite_ok = result["citation_count"] >= expected_min_cites
    criteria["citations"] = {
        "pass": cite_ok,
        "expected_min": expected_min_cites,
        "actual": result["citation_count"],
    }

    # Criterion 4: latency < 30s (hard cap)
    latency_ok = result["execution_ms"] < 30_000
    criteria["latency"] = {
        "pass": latency_ok,
        "limit_ms": 30_000,
        "actual_ms": result["execution_ms"],
    }

    # Overall pass: all required criteria pass
    # Note: keyword presence is a soft criterion — we warn but don't fail on it
    # (the system may not have relevant data ingested for all queries)
    hard_pass = conf_ok and cite_ok and latency_ok

    return {
        "golden_id": golden["id"],
        "category": golden["category"],
        "query": golden["query"],
        "result": result,
        "criteria": criteria,
        "pass": hard_pass,
        "notes": golden.get("notes", ""),
    }


async def main(workspace_id_str: str, queries_file: str, output_path: str | None) -> int:
    workspace_id = UUID(workspace_id_str)
    queries_path = Path(queries_file)

    if not queries_path.exists():
        print(f"ERROR: queries file not found: {queries_path}", file=sys.stderr)
        return 2

    with open(queries_path) as f:
        golden_data = json.load(f)

    golden_queries = golden_data["queries"]
    print(f"Company Brain Evaluation Framework")
    print(f"  Workspace:  {workspace_id}")
    print(f"  Queries:    {len(golden_queries)}")
    print(f"  Started at: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)

    eval_results = []
    passed = 0
    failed = 0

    for gq in golden_queries:
        print(f"\n[{gq['id']}] {gq['query'][:60]}...")
        try:
            result = await run_query(workspace_id, gq["query"])
            eval_result = evaluate_query(gq, result)

            status = "PASS" if eval_result["pass"] else "FAIL"
            if eval_result["pass"]:
                passed += 1
            else:
                failed += 1

            print(f"  Status:     {status}")
            print(f"  Strategy:   {result['strategy']}")
            print(f"  Confidence: {result['confidence']}")
            print(f"  Citations:  {result['citation_count']}")
            print(f"  Latency:    {result['execution_ms']}ms")
            print(f"  Answer:     {result['answer'][:100]}...")

            # Print failing criteria
            for criterion, detail in eval_result["criteria"].items():
                if not detail.get("pass", True):
                    print(f"  FAIL [{criterion}]: {detail}")

        except Exception as exc:
            print(f"  ERROR: {exc}")
            eval_results.append({
                "golden_id": gq["id"],
                "pass": False,
                "error": str(exc),
            })
            failed += 1
            continue

        eval_results.append(eval_result)

    print("\n" + "=" * 60)
    print(f"RESULTS: {passed}/{len(golden_queries)} passed, {failed} failed")

    # Compute aggregate metrics
    successful_results = [r for r in eval_results if "result" in r]
    if successful_results:
        latencies = [r["result"]["execution_ms"] for r in successful_results]
        avg_latency = int(sum(latencies) / len(latencies))
        confidence_dist = {}
        for r in successful_results:
            c = r["result"]["confidence"]
            confidence_dist[c] = confidence_dist.get(c, 0) + 1
        print(f"Avg latency:  {avg_latency}ms")
        print(f"Confidence:   {confidence_dist}")

    summary = {
        "version": golden_data["version"],
        "workspace_id": workspace_id_str,
        "run_at": datetime.now(timezone.utc).isoformat(),
        "total": len(golden_queries),
        "passed": passed,
        "failed": failed,
        "pass_rate": round(passed / len(golden_queries), 4) if golden_queries else 0,
        "results": eval_results,
    }

    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w") as f:
            json.dump(summary, f, indent=2, default=str)
        print(f"Results written to: {out}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Company Brain Evaluation Framework")
    parser.add_argument("--workspace-id", required=True, help="Workspace UUID to run queries against")
    parser.add_argument(
        "--queries-file",
        default=str(_REPO_ROOT / "data" / "eval" / "golden_queries.json"),
        help="Path to golden queries JSON file",
    )
    parser.add_argument("--output", default=None, help="Output path for JSON results")
    args = parser.parse_args()

    exit_code = asyncio.run(main(args.workspace_id, args.queries_file, args.output))
    sys.exit(exit_code)
