"""Integration tests for Observability — metrics endpoint and latency middleware.

Tests:
  GET /api/v1/metrics        → system metrics + per-endpoint request tracking
  GET /api/v1/metrics/health-summary → lightweight health summary
  X-Response-Time-Ms header  → latency middleware fires on every response
"""
import pytest
from fastapi.testclient import TestClient
from backend.main import app


@pytest.fixture(scope="module")
def client():
    import asyncio
    from backend.db.session import engine as db_engine
    with TestClient(app) as c:
        yield c
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(db_engine.dispose())
    finally:
        loop.close()


class TestMetricsEndpoint:
    def test_metrics_returns_200(self, client):
        r = client.get("/api/v1/metrics")
        assert r.status_code == 200

    def test_metrics_has_system_block(self, client):
        r = client.get("/api/v1/metrics")
        data = r.json()
        assert "system" in data
        assert "service" in data["system"]
        assert data["system"]["service"] == "company-brain"
        print(f"\n  [METRICS] system: {list(data['system'].keys())}")

    def test_metrics_has_requests_block(self, client):
        # Hit an endpoint first to seed request data
        client.get("/health")
        r = client.get("/api/v1/metrics")
        data = r.json()
        assert "requests" in data
        assert "uptime_seconds" in data
        assert isinstance(data["uptime_seconds"], int)
        print(f"\n  [METRICS] uptime={data['uptime_seconds']}s, endpoints tracked={data['endpoint_count']}")

    def test_metrics_tracks_request_counts(self, client):
        """Fire 3 health requests, then verify metrics counted them."""
        for _ in range(3):
            client.get("/health")

        r = client.get("/api/v1/metrics")
        data = r.json()
        # /health should appear in request metrics
        health_metrics = data["requests"].get("/health", {})
        assert health_metrics.get("count", 0) >= 3
        print(f"\n  [METRICS] /health count: {health_metrics.get('count')}")

    def test_metrics_has_latency_percentiles(self, client):
        client.get("/health")
        r = client.get("/api/v1/metrics")
        data = r.json()
        health = data["requests"].get("/health", {})
        assert "latency_ms" in health
        latency = health["latency_ms"]
        assert "p50" in latency
        assert "p95" in latency
        assert "p99" in latency
        assert latency["p50"] >= 0
        print(f"\n  [METRICS] /health latency: {latency}")


class TestHealthSummary:
    def test_health_summary_returns_200(self, client):
        r = client.get("/api/v1/metrics/health-summary")
        assert r.status_code == 200

    def test_health_summary_structure(self, client):
        r = client.get("/api/v1/metrics/health-summary")
        data = r.json()
        assert data["status"] == "ok"
        assert "uptime_seconds" in data
        assert "total_requests" in data
        assert "total_errors" in data
        assert "error_rate" in data
        assert isinstance(data["total_requests"], int)
        assert data["total_requests"] >= 0
        print(f"\n  [METRICS] summary: requests={data['total_requests']}, errors={data['total_errors']}")


class TestLatencyMiddleware:
    def test_x_response_time_header_present(self, client):
        """Every response should carry X-Response-Time-Ms header."""
        r = client.get("/health")
        assert "x-response-time-ms" in r.headers
        latency = int(r.headers["x-response-time-ms"])
        assert latency >= 0
        print(f"\n  [METRICS] X-Response-Time-Ms: {latency}ms")

    def test_latency_header_on_api_endpoint(self, client):
        """API endpoints also get the header."""
        r = client.get("/api/v1/workspaces")
        assert "x-response-time-ms" in r.headers

    def test_path_normalization(self, client):
        """UUID segments are normalized to {id} in metrics keys."""
        from uuid import uuid4
        # Hit an endpoint with a UUID in the path
        client.get(f"/api/v1/workspaces/{uuid4()}")
        r = client.get("/api/v1/metrics")
        data = r.json()
        # Should see /api/v1/workspaces/{id} not the raw UUID
        paths = list(data["requests"].keys())
        uuid_paths = [p for p in paths if len(p) > 36 and "-" in p.split("/")[-1]]
        assert len(uuid_paths) == 0, f"Raw UUIDs found in metric paths: {uuid_paths}"
        normalized = [p for p in paths if "{id}" in p]
        print(f"\n  [METRICS] normalized paths: {normalized}")
