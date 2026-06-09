"""Unit tests for backend/core/rate_limiter.py

Verifies limiter configuration constants, the key function logic,
and that the limiter instance is a proper slowapi Limiter.
"""
import pytest
from unittest.mock import MagicMock


class TestRateLimiterConfig:
    def test_limiter_is_slowapi_limiter(self):
        from slowapi import Limiter
        from backend.core.rate_limiter import limiter
        assert isinstance(limiter, Limiter)

    def test_query_rate_format(self):
        from backend.core.rate_limiter import QUERY_RATE
        assert "/" in QUERY_RATE
        count, period = QUERY_RATE.split("/")
        assert int(count) > 0

    def test_auth_rate_format(self):
        from backend.core.rate_limiter import AUTH_RATE
        count, period = AUTH_RATE.split("/")
        assert int(count) > 0

    def test_admin_rate_is_restrictive(self):
        """Admin rate should be lower than query rate."""
        from backend.core.rate_limiter import ADMIN_RATE, QUERY_RATE
        admin_count = int(ADMIN_RATE.split("/")[0])
        query_count = int(QUERY_RATE.split("/")[0])
        assert admin_count <= query_count

    def test_auth_rate_is_restrictive(self):
        """Auth rate should be lowest to prevent brute-force."""
        from backend.core.rate_limiter import AUTH_RATE, READ_RATE
        auth_count = int(AUTH_RATE.split("/")[0])
        read_count = int(READ_RATE.split("/")[0])
        assert auth_count < read_count


class TestRateLimitKeyFunction:
    def test_no_api_key_falls_back_to_ip(self):
        """Without X-API-Key header, key is the client IP."""
        from backend.core.rate_limiter import _get_rate_limit_key
        mock_request = MagicMock()
        mock_request.headers = {}  # No X-API-Key
        mock_request.client = MagicMock()
        mock_request.client.host = "10.0.0.1"
        # Should call get_remote_address fallback path
        # Result should not be "apikey:" prefixed
        key = _get_rate_limit_key(mock_request)
        assert not key.startswith("apikey:")

    def test_with_api_key_uses_hash_prefix(self):
        """With X-API-Key header, key is 'apikey:' + hash prefix."""
        from backend.core.rate_limiter import _get_rate_limit_key
        mock_request = MagicMock()
        mock_request.headers = {"X-API-Key": "cb_test_key_12345"}
        mock_request.client = MagicMock()
        mock_request.client.host = "10.0.0.1"
        key = _get_rate_limit_key(mock_request)
        assert key.startswith("apikey:")
        assert len(key) > 7  # "apikey:" is 7 chars

    def test_same_key_produces_same_rate_limit_key(self):
        """Same raw key always maps to the same rate limit bucket."""
        from backend.core.rate_limiter import _get_rate_limit_key
        raw_key = "cb_consistent_key_for_test"
        mock1 = MagicMock()
        mock1.headers = {"X-API-Key": raw_key}
        mock2 = MagicMock()
        mock2.headers = {"X-API-Key": raw_key}
        assert _get_rate_limit_key(mock1) == _get_rate_limit_key(mock2)

    def test_different_keys_produce_different_buckets(self):
        """Different raw keys map to different rate limit buckets."""
        from backend.core.rate_limiter import _get_rate_limit_key
        mock1 = MagicMock()
        mock1.headers = {"X-API-Key": "cb_key_one"}
        mock2 = MagicMock()
        mock2.headers = {"X-API-Key": "cb_key_two"}
        assert _get_rate_limit_key(mock1) != _get_rate_limit_key(mock2)
