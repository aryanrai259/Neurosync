# Purpose:      Unit tests for core/config.py — Settings class and get_settings()
# Tests:        Default values, env var overrides, caching behaviour, validation
# Dependencies: pytest, pydantic-settings
# Run with:     pytest tests/unit/core/test_config.py -v --cov=backend/core/config

import pytest

from backend.core.config import Settings, get_settings
from backend.models.enums import LLMProvider, VectorStore


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear lru_cache before and after every test for isolation."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


# ─── Default values ───────────────────────────────────────────────────────────


class TestSettingsDefaults:
    def test_app_name_default(self):
        s = Settings()
        assert s.app_name == "Company Brain"

    def test_app_version_default(self):
        s = Settings()
        assert s.app_version == "0.4.0"

    def test_debug_is_false_by_default(self):
        s = Settings()
        assert s.debug is False

    def test_log_level_default(self):
        s = Settings()
        assert s.log_level == "INFO"

    def test_default_llm_provider(self):
        s = Settings()
        assert s.default_llm_provider == LLMProvider.OPENAI

    def test_default_llm_model(self):
        s = Settings()
        assert s.default_llm_model == "gpt-4o"

    def test_default_vector_store(self):
        s = Settings()
        assert s.default_vector_store == VectorStore.PGVECTOR

    def test_default_retention_days(self):
        s = Settings()
        assert s.default_retention_days == 365

    def test_default_max_context_tokens(self):
        s = Settings()
        assert s.default_max_context_tokens == 8000


# ─── Environment variable overrides ───────────────────────────────────────────


class TestSettingsEnvOverrides:
    def test_override_debug_via_env(self, monkeypatch):
        monkeypatch.setenv("DEBUG", "true")
        s = Settings()
        assert s.debug is True

    def test_override_log_level_via_env(self, monkeypatch):
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        s = Settings()
        assert s.log_level == "DEBUG"

    def test_override_llm_provider_via_env(self, monkeypatch):
        monkeypatch.setenv("DEFAULT_LLM_PROVIDER", "gemini")
        s = Settings()
        assert s.default_llm_provider == LLMProvider.GEMINI

    def test_override_llm_model_via_env(self, monkeypatch):
        monkeypatch.setenv("DEFAULT_LLM_MODEL", "gemini-1.5-pro")
        s = Settings()
        assert s.default_llm_model == "gemini-1.5-pro"

    def test_override_vector_store_via_env(self, monkeypatch):
        monkeypatch.setenv("DEFAULT_VECTOR_STORE", "qdrant")
        s = Settings()
        assert s.default_vector_store == VectorStore.QDRANT

    def test_override_retention_days_via_env(self, monkeypatch):
        monkeypatch.setenv("DEFAULT_RETENTION_DAYS", "180")
        s = Settings()
        assert s.default_retention_days == 180

    def test_override_max_context_tokens_via_env(self, monkeypatch):
        monkeypatch.setenv("DEFAULT_MAX_CONTEXT_TOKENS", "16000")
        s = Settings()
        assert s.default_max_context_tokens == 16000

    def test_env_var_is_case_insensitive(self, monkeypatch):
        monkeypatch.setenv("default_llm_model", "gpt-3.5-turbo")
        s = Settings()
        assert s.default_llm_model == "gpt-3.5-turbo"

    def test_unknown_env_vars_are_ignored(self, monkeypatch):
        monkeypatch.setenv("COMPLETELY_UNKNOWN_VAR", "xyz")
        s = Settings()  # should not raise
        assert s is not None


# ─── Validation ───────────────────────────────────────────────────────────────


class TestSettingsValidation:
    def test_invalid_llm_provider_raises(self, monkeypatch):
        monkeypatch.setenv("DEFAULT_LLM_PROVIDER", "grok")
        with pytest.raises(Exception):
            Settings()

    def test_retention_days_below_minimum_raises(self, monkeypatch):
        monkeypatch.setenv("DEFAULT_RETENTION_DAYS", "0")
        with pytest.raises(Exception):
            Settings()

    def test_retention_days_above_maximum_raises(self, monkeypatch):
        monkeypatch.setenv("DEFAULT_RETENTION_DAYS", "9999")
        with pytest.raises(Exception):
            Settings()

    def test_max_context_tokens_below_minimum_raises(self, monkeypatch):
        monkeypatch.setenv("DEFAULT_MAX_CONTEXT_TOKENS", "500")
        with pytest.raises(Exception):
            Settings()


# ─── get_settings() caching ───────────────────────────────────────────────────


class TestGetSettings:
    def test_returns_settings_instance(self):
        s = get_settings()
        assert isinstance(s, Settings)

    def test_returns_same_instance_on_repeated_calls(self):
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2

    def test_cache_clear_returns_fresh_instance(self):
        s1 = get_settings()
        get_settings.cache_clear()
        s2 = get_settings()
        # Both valid Settings, but different objects after cache clear
        assert isinstance(s2, Settings)
        assert s1 is not s2
