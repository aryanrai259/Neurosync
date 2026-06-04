# Purpose:      Unit tests for models/workspace.py and models/enums.py
# Tests:        WorkspaceConfig defaults, Workspace defaults,
#               slug validation, field constraints, enum values
# Dependencies: pytest, pydantic v2
# Run with:     pytest tests/unit/models/test_workspace.py -v

import pytest
from uuid import UUID
from datetime import datetime, timezone

from pydantic import ValidationError

from backend.models.enums import (
    EntityType,
    LLMProvider,
    SourceType,
    VectorStore,
)
from backend.models.workspace import Workspace, WorkspaceConfig


# ─── WorkspaceConfig ──────────────────────────────────────────────────────────


class TestWorkspaceConfig:
    def test_default_enabled_sources_is_empty(self):
        config = WorkspaceConfig()
        assert config.enabled_sources == []

    def test_default_llm_provider_is_openai(self):
        config = WorkspaceConfig()
        assert config.llm_provider == LLMProvider.OPENAI

    def test_default_llm_model_is_gpt4o(self):
        config = WorkspaceConfig()
        assert config.llm_model == "gpt-4o"

    def test_default_vector_store_is_chroma(self):
        config = WorkspaceConfig()
        assert config.vector_store == VectorStore.CHROMA

    def test_default_retention_days_is_365(self):
        config = WorkspaceConfig()
        assert config.retention_days == 365

    def test_default_max_context_tokens_is_8000(self):
        config = WorkspaceConfig()
        assert config.max_context_tokens == 8000

    def test_enabled_sources_accepts_valid_list(self):
        config = WorkspaceConfig(
            enabled_sources=[SourceType.SLACK, SourceType.GITHUB]
        )
        assert SourceType.SLACK in config.enabled_sources
        assert SourceType.GITHUB in config.enabled_sources

    def test_invalid_llm_provider_raises(self):
        with pytest.raises(ValidationError):
            WorkspaceConfig(llm_provider="grok")  # type: ignore

    def test_retention_days_below_minimum_raises(self):
        with pytest.raises(ValidationError):
            WorkspaceConfig(retention_days=0)

    def test_retention_days_above_maximum_raises(self):
        with pytest.raises(ValidationError):
            WorkspaceConfig(retention_days=9999)

    def test_max_context_tokens_below_minimum_raises(self):
        with pytest.raises(ValidationError):
            WorkspaceConfig(max_context_tokens=500)

    def test_config_is_immutable(self):
        config = WorkspaceConfig()
        with pytest.raises(ValidationError):
            config.llm_model = "claude-3"  # type: ignore

    def test_all_source_types_accepted(self):
        config = WorkspaceConfig(enabled_sources=list(SourceType))
        assert len(config.enabled_sources) == len(SourceType)


# ─── Workspace ────────────────────────────────────────────────────────────────


class TestWorkspace:
    def _make(self, **kwargs) -> Workspace:
        defaults = dict(name="Acme Corp", slug="acme-corp", owner_id="user-123")
        return Workspace(**{**defaults, **kwargs})

    def test_id_is_uuid(self):
        ws = self._make()
        assert isinstance(ws.id, UUID)

    def test_each_workspace_gets_unique_id(self):
        ws1 = self._make()
        ws2 = self._make()
        assert ws1.id != ws2.id

    def test_is_active_by_default(self):
        ws = self._make()
        assert ws.is_active is True

    def test_config_defaults_are_applied(self):
        ws = self._make()
        assert isinstance(ws.config, WorkspaceConfig)
        assert ws.config.llm_provider == LLMProvider.OPENAI

    def test_created_at_is_utc(self):
        ws = self._make()
        assert ws.created_at.tzinfo == timezone.utc

    def test_updated_at_is_utc(self):
        ws = self._make()
        assert ws.updated_at.tzinfo == timezone.utc

    def test_workspace_is_immutable(self):
        ws = self._make()
        with pytest.raises(ValidationError):
            ws.name = "New Name"  # type: ignore

    def test_name_too_long_raises(self):
        with pytest.raises(ValidationError):
            self._make(name="x" * 129)

    def test_name_empty_raises(self):
        with pytest.raises(ValidationError):
            self._make(name="")

    # ── Slug validation ───────────────────────────────────────────────────────

    def test_valid_slug_lowercase_hyphen(self):
        ws = self._make(slug="acme-corp")
        assert ws.slug == "acme-corp"

    def test_valid_slug_single_word(self):
        ws = self._make(slug="acme")
        assert ws.slug == "acme"

    def test_valid_slug_numbers(self):
        ws = self._make(slug="team-42")
        assert ws.slug == "team-42"

    def test_slug_uppercase_raises(self):
        with pytest.raises(ValidationError):
            self._make(slug="Acme-Corp")

    def test_slug_leading_hyphen_raises(self):
        with pytest.raises(ValidationError):
            self._make(slug="-acme")

    def test_slug_trailing_hyphen_raises(self):
        with pytest.raises(ValidationError):
            self._make(slug="acme-")

    def test_slug_consecutive_hyphens_raises(self):
        with pytest.raises(ValidationError):
            self._make(slug="acme--corp")

    def test_slug_spaces_raises(self):
        with pytest.raises(ValidationError):
            self._make(slug="acme corp")

    def test_slug_too_long_raises(self):
        with pytest.raises(ValidationError):
            self._make(slug="a" * 65)

    def test_custom_config_is_stored(self):
        config = WorkspaceConfig(
            enabled_sources=[SourceType.SLACK],
            llm_provider=LLMProvider.GEMINI,
        )
        ws = self._make(config=config)
        assert ws.config.llm_provider == LLMProvider.GEMINI
        assert SourceType.SLACK in ws.config.enabled_sources


# ─── SourceType enum ──────────────────────────────────────────────────────────


class TestSourceTypeEnum:
    def test_all_expected_values_exist(self):
        values = {e.value for e in SourceType}
        assert values == {"slack", "github", "jira", "notion", "email"}

    def test_source_type_is_string(self):
        assert isinstance(SourceType.SLACK, str)
        assert SourceType.SLACK == "slack"


# ─── EntityType enum ──────────────────────────────────────────────────────────


class TestEntityTypeEnum:
    def test_all_expected_values_exist(self):
        values = {e.value for e in EntityType}
        assert values == {
            "person", "service", "repository",
            "ticket", "decision", "document", "team",
        }
