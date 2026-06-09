# Purpose:      Observability API — system metrics and request latency endpoints.
#               Exposes /api/v1/metrics for monitoring tools (Prometheus, Grafana, etc.)
#               All values are collected from live process state — no external storage.
# Called By:    backend/main.py (router)
# Calls:        core/telemetry.py
# Dependencies: fastapi
# Test File:    tests/integration/api/test_observability.py

import logging
import time

from fastapi import APIRouter

from backend.core.telemetry import collect_system_metrics

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/metrics", tags=["observability"])

# ---------------------------------------------------------------------------
# In-process request counter — updated by RequestLatencyMiddleware
# ---------------------------------------------------------------------------
_request_counts: dict[str, int] = {}      # path → count
_request_latencies: dict[str, list[int]] = {}  # path → [ms, ...]
_error_counts: dict[str, int] = {}        # path → error count
_server_start_time: float = time.time()


def record_request(path: str, status_code: int, latency_ms: int) -> None:
    """
    Record a completed request. Called by RequestLatencyMiddleware.
    Thread-safe only for single-process deployments (GIL protects dict ops).
    """
    _request_counts[path] = _request_counts.get(path, 0) + 1
    if path not in _request_latencies:
        _request_latencies[path] = []
    _request_latencies[path].append(latency_ms)
    # Keep only last 1000 latencies per path (memory cap)
    if len(_request_latencies[path]) > 1000:
        _request_latencies[path] = _request_latencies[path][-1000:]
    if status_code >= 400:
        _error_counts[path] = _error_counts.get(path, 0) + 1


def _percentile(values: list[int], p: float) -> int:
    """Compute percentile p (0–100) from a sorted list."""
    if not values:
        return 0
    sorted_vals = sorted(values)
    idx = max(0, int(len(sorted_vals) * p / 100) - 1)
    return sorted_vals[idx]


# ---------------------------------------------------------------------------
# Metrics endpoint
# ---------------------------------------------------------------------------

@router.get(
    "",
    summary="System and request metrics",
    description=(
        "Returns process-level metrics (memory, GC, Python version) and "
        "per-endpoint request counts, latency percentiles, and error rates. "
        "Suitable for polling by Prometheus or health dashboards."
    ),
)
async def get_metrics() -> dict:
    """
    Collect and return all system and request metrics.

    Returns:
        system: Process memory, CPU, GC stats.
        requests: Per-endpoint counts, p50/p95/p99 latencies, error rates.
        uptime_seconds: Time since server start.
    """
    system = collect_system_metrics()

    request_metrics = {}
    for path, count in _request_counts.items():
        latencies = _request_latencies.get(path, [])
        errors = _error_counts.get(path, 0)
        request_metrics[path] = {
            "count": count,
            "error_count": errors,
            "error_rate": round(errors / count, 4) if count > 0 else 0,
            "latency_ms": {
                "p50": _percentile(latencies, 50),
                "p95": _percentile(latencies, 95),
                "p99": _percentile(latencies, 99),
                "min": min(latencies) if latencies else 0,
                "max": max(latencies) if latencies else 0,
            },
        }

    uptime = int(time.time() - _server_start_time)

    logger.debug("Metrics collected: %d endpoints tracked", len(request_metrics))

    return {
        "system": system,
        "requests": request_metrics,
        "uptime_seconds": uptime,
        "endpoint_count": len(request_metrics),
    }


@router.get(
    "/health-summary",
    summary="Lightweight health summary for dashboards",
)
async def health_summary() -> dict:
    """
    Fast health summary — total requests, total errors, uptime.
    No per-endpoint breakdown. Suitable for status page polling.
    """
    total_requests = sum(_request_counts.values())
    total_errors = sum(_error_counts.values())
    error_rate = round(total_errors / total_requests, 4) if total_requests > 0 else 0

    return {
        "status": "ok",
        "uptime_seconds": int(time.time() - _server_start_time),
        "total_requests": total_requests,
        "total_errors": total_errors,
        "error_rate": error_rate,
    }
