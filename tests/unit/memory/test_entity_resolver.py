# Purpose:      Unit tests for memory/entity_resolver.py
# Tests:        All three extraction tiers, deduplication, alias warnings,
#               edge cases (empty content, unknown author, etc.)
# Run with:     pytest tests/unit/memory/test_entity_resolver.py -v

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from backend.memory.entity_resolver import (
    EntityResolver,
    _deduplicate,
    _extract_from_patterns,
    _extract_from_seed_lists,
    _extract_from_structured_fields,
)
from backend.memory.memory_object import EntityRef
from backend.models.enums import EntityType, SourceType
from backend.models.event import NormalizedEvent


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _make_event(**kwargs) -> NormalizedEvent:
    defaults = dict(
        source=SourceType.SLACK,
        workspace_id=uuid4(),
        source_id="ts-12345",
        content="auth-service is down, contacting platform-team",
        author_id="alice",
        timestamp=datetime.now(timezone.utc),
    )
    return NormalizedEvent(**{**defaults, **kwargs})


def _make_github_event(**kwargs) -> NormalizedEvent:
    defaults = dict(
        source=SourceType.GITHUB,
        workspace_id=uuid4(),
        source_id="sha-abc123",
        content="Fix bug in auth-service. References PROJ-42.",
        author_id="bob",
        timestamp=datetime.now(timezone.utc),
        metadata={"repo": "acme/auth-service", "labels": []},
    )
    return NormalizedEvent(**{**defaults, **kwargs})


# ─── Tier 1: Structured field extraction ──────────────────────────────────────

class TestStructuredFieldExtraction:
    def test_author_extracted_as_person(self):
        event = _make_event(author_id="alice")
        refs = _extract_from_structured_fields(event)
        names = [r.canonical_name for r in refs]
        assert "alice" in names

    def test_author_has_confidence_1(self):
        event = _make_event(author_id="alice")
        refs = _extract_from_structured_fields(event)
        person = next(r for r in refs if r.entity_type == EntityType.PERSON)
        assert person.confidence == 1.0

    def test_author_extraction_source_is_structured(self):
        event = _make_event(author_id="alice")
        refs = _extract_from_structured_fields(event)
        person = next(r for r in refs if r.entity_type == EntityType.PERSON)
        assert "structured" in person.extraction_source

    def test_bot_author_not_extracted(self):
        event = _make_event(author_id="bot")
        refs = _extract_from_structured_fields(event)
        assert not any(r.entity_type == EntityType.PERSON for r in refs)

    def test_system_author_not_extracted(self):
        event = _make_event(author_id="system")
        refs = _extract_from_structured_fields(event)
        assert not any(r.entity_type == EntityType.PERSON for r in refs)

    def test_github_repo_extracted(self):
        event = _make_github_event(metadata={"repo": "acme/auth-service", "labels": []})
        refs = _extract_from_structured_fields(event)
        repos = [r for r in refs if r.entity_type == EntityType.REPOSITORY]
        assert any("acme/auth-service" in r.canonical_name for r in repos)

    def test_github_decision_label_extracted(self):
        event = _make_github_event(metadata={"repo": "acme/r", "labels": ["decision"]})
        refs = _extract_from_structured_fields(event)
        decisions = [r for r in refs if r.entity_type == EntityType.DECISION]
        assert len(decisions) == 1

    def test_non_github_repo_not_extracted(self):
        event = _make_event(metadata={"repo": "acme/auth-service"})
        refs = _extract_from_structured_fields(event)
        repos = [r for r in refs if r.entity_type == EntityType.REPOSITORY]
        assert len(repos) == 0


# ─── Tier 2: Seed list matching ───────────────────────────────────────────────

class TestSeedListExtraction:
    def test_known_service_matched(self):
        refs = _extract_from_seed_lists(
            "auth-service is down", ["auth-service"], []
        )
        assert any(r.canonical_name == "auth-service" for r in refs)

    def test_known_team_matched(self):
        refs = _extract_from_seed_lists(
            "platform-team escalated", [], ["platform-team"]
        )
        assert any(r.entity_type == EntityType.TEAM for r in refs)

    def test_case_insensitive_match(self):
        refs = _extract_from_seed_lists("AUTH-SERVICE is down", ["auth-service"], [])
        assert len(refs) >= 1

    def test_no_match_returns_empty(self):
        refs = _extract_from_seed_lists("random text", ["auth-service"], [])
        assert refs == []

    def test_tech_name_redis_matched(self):
        refs = _extract_from_seed_lists("migrating to redis", [], [])
        assert any(r.canonical_name == "redis" for r in refs)

    def test_seed_confidence_is_1(self):
        refs = _extract_from_seed_lists("auth-service", ["auth-service"], [])
        assert all(r.confidence == 1.0 for r in refs)


# ─── Tier 3: Pattern matching ─────────────────────────────────────────────────

class TestPatternExtraction:
    def test_ticket_pattern_matched(self):
        refs = _extract_from_patterns("see PROJ-1234 for context", SourceType.SLACK)
        tickets = [r for r in refs if r.entity_type == EntityType.TICKET]
        assert any(r.canonical_name == "PROJ-1234" for r in tickets)

    def test_ticket_pattern_case_uppercase_only(self):
        refs = _extract_from_patterns("proj-1234 is invalid", SourceType.SLACK)
        tickets = [r for r in refs if r.entity_type == EntityType.TICKET]
        assert len(tickets) == 0  # lowercase proj-1234 doesn't match [A-Z]{2,10}

    def test_mention_in_slack_matched(self):
        refs = _extract_from_patterns("@alice please review", SourceType.SLACK)
        persons = [r for r in refs if r.entity_type == EntityType.PERSON]
        assert any(r.canonical_name == "alice" for r in persons)

    def test_mention_in_github_not_extracted(self):
        # @mentions are only extracted from Slack
        refs = _extract_from_patterns("@alice please review", SourceType.GITHUB)
        persons = [r for r in refs if r.entity_type == EntityType.PERSON]
        assert len(persons) == 0

    def test_here_mention_not_extracted(self):
        refs = _extract_from_patterns("@here is a broadcast", SourceType.SLACK)
        assert all(r.canonical_name != "here" for r in refs)

    def test_pattern_confidence_is_0_85(self):
        refs = _extract_from_patterns("see PROJ-99 for context", SourceType.SLACK)
        assert all(r.confidence == 0.85 for r in refs)


# ─── Deduplication ────────────────────────────────────────────────────────────

class TestDeduplication:
    def _ref(self, name, entity_type=EntityType.SERVICE, confidence=1.0):
        return EntityRef(
            canonical_name=name,
            entity_type=entity_type,
            confidence=confidence,
            extraction_source="test",
        )

    def test_duplicate_same_name_type_kept_once(self):
        refs = [
            self._ref("auth-service", confidence=1.0),
            self._ref("auth-service", confidence=0.85),
        ]
        deduped = _deduplicate(refs)
        auth_refs = [r for r in deduped if r.canonical_name == "auth-service"]
        assert len(auth_refs) == 1

    def test_highest_confidence_kept(self):
        refs = [
            self._ref("auth-service", confidence=0.85),
            self._ref("auth-service", confidence=1.0),
        ]
        deduped = _deduplicate(refs)
        auth = next(r for r in deduped if r.canonical_name == "auth-service")
        assert auth.confidence == 1.0

    def test_different_types_both_kept(self):
        refs = [
            self._ref("alice", EntityType.PERSON),
            self._ref("alice", EntityType.TEAM),
        ]
        deduped = _deduplicate(refs)
        assert len(deduped) == 2


# ─── Full resolver integration ────────────────────────────────────────────────

class TestEntityResolverFull:
    def test_resolve_returns_list(self):
        resolver = EntityResolver()
        event = _make_event()
        result = resolver.resolve(event)
        assert isinstance(result, list)

    def test_resolve_finds_service(self):
        resolver = EntityResolver()
        event = _make_event(content="auth-service is failing")
        result = resolver.resolve(event)
        names = [r.canonical_name for r in result]
        assert "auth-service" in names

    def test_resolve_finds_author(self):
        resolver = EntityResolver()
        event = _make_event(author_id="alice")
        result = resolver.resolve(event)
        names = [r.canonical_name for r in result]
        assert "alice" in names

    def test_resolve_empty_content_no_seed_match(self):
        resolver = EntityResolver(service_names=[], team_names=[])
        event = _make_event(content="nothing to see here", author_id="bot")
        result = resolver.resolve(event)
        assert result == []

    def test_resolve_github_extracts_repo(self):
        resolver = EntityResolver()
        event = _make_github_event()
        result = resolver.resolve(event)
        repos = [r for r in result if r.entity_type == EntityType.REPOSITORY]
        assert len(repos) >= 1
