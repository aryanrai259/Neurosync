"""Unit tests for backend/core/auth.py — API key generation and hashing."""
import pytest

from backend.core.auth import generate_api_key, hash_api_key, _hash_key


def test_generate_api_key_returns_two_strings():
    """generate_api_key() returns (raw_key, key_hash)."""
    raw, hashed = generate_api_key()
    assert isinstance(raw, str)
    assert isinstance(hashed, str)


def test_raw_key_has_prefix():
    """Generated raw keys start with 'cb_' prefix."""
    raw, _ = generate_api_key()
    assert raw.startswith("cb_")


def test_raw_key_sufficient_length():
    """Raw key is long enough to be secure (>= 40 chars)."""
    raw, _ = generate_api_key()
    assert len(raw) >= 40


def test_hash_is_64_hex_chars():
    """SHA-256 hash produces a 64-character hexadecimal string."""
    _, hashed = generate_api_key()
    assert len(hashed) == 64
    assert all(c in "0123456789abcdef" for c in hashed)


def test_two_keys_are_different():
    """Each call generates a unique key (collision probability negligible)."""
    raw1, _ = generate_api_key()
    raw2, _ = generate_api_key()
    assert raw1 != raw2


def test_hash_api_key_matches_stored_hash():
    """hash_api_key(raw) must match the hash returned by generate_api_key()."""
    raw, stored_hash = generate_api_key()
    assert hash_api_key(raw) == stored_hash


def test_wrong_key_does_not_match():
    """A different raw key produces a different hash (no collision)."""
    raw, stored_hash = generate_api_key()
    assert hash_api_key("wrong_key") != stored_hash


def test_hash_is_deterministic():
    """Same raw key always produces the same hash."""
    test_key = "cb_testkey123"
    assert hash_api_key(test_key) == hash_api_key(test_key)
    assert hash_api_key(test_key) == _hash_key(test_key)
