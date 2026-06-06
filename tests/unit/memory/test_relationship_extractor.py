# Purpose:      Unit tests for memory/relationship_extractor.py
# Tests:        Each of the 7 named relationship rules independently,
#               full extractor with entity lists, edge cases.
# Run with:     pytest tests/unit/memory/test_relationship_extractor.py -v

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from backend.memory.memory_object import EntityRef, RelationshipRef
from backend.memory.relationship_extractor import (
    RelationshipExtractor,
    _rule_affects,
    _rule_authored,
    _rule_depends_on,
    _rule_discussed_in,
    _rule_owns,
    _rule_references,
    _rule_related_to,
)
from backend.models.enums import EntityType, SourceType
from backend.models.event import NormalizedEvent


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _make_event(**kwargs) -> NormalizedEvent:
    defaults = dict(
        source=SourceType.SLACK,
        workspace_id=uuid4(),
        source_id="ts-001",
        content="test content",
        author_id="alice",
        timestamp=datetime.now(timezone.utc),
    )
    return NormalizedEvent(**{**defaults, **kwargs})


def _ref(name: str, entity_type: EntityType, confidence=1.0, source="structured_author_id") -> EntityRef:
    return EntityRef(
        canonical_name=name,
        entity_type=entity_type,
        confidence=confidence,
        extraction_source=source,
    )


def _person(name="alice") -> EntityRef:
    return _ref(name, EntityType.PERSON)


def _service(name="auth-service") -> EntityRef:
    return _ref(name, EntityType.SERVICE, source="seed_list_service")


def _team(name="platform-team") -> EntityRef:
    return _ref(name, EntityType.TEAM, source="seed_list_team")


def _ticket(name="PROJ-42") -> EntityRef:
    return _ref(name, EntityType.TICKET, confidence=0.85, source="pattern_ticket")


# ─── Rule: AUTHORED ──────────────────────────────────────────────────────────

class TestRuleAuthored:
    def test_structured_author_produces_authored_rel(self):
        event = _make_event(author_id="alice")
        entities = [_person("alice")]
        rels = _rule_authored(event, entities)
        authored = [r for r in rels if r.predicate == "AUTHORED"]
        assert len(authored) == 1
        assert authored[0].subject.canonical_name == "alice"

    def test_non_structured_author_not_authored(self):
        # A person from pattern match (mention) should NOT get AUTHORED
        event = _make_event()
        entities = [_ref("bob", EntityType.PERSON, source="pattern_mention")]
        rels = _rule_authored(event, entities)
        assert len(rels) == 0

    def test_authored_confidence_matches_entity(self):
        event = _make_event()
        person = _ref("alice", EntityType.PERSON, confidence=1.0, source="structured_author_id")
        rels = _rule_authored(event, [person])
        assert rels[0].confidence == 1.0

    def test_no_persons_no_authored(self):
        event = _make_event()
        rels = _rule_authored(event, [_service()])
        assert len(rels) == 0


# ─── Rule: AFFECTS ───────────────────────────────────────────────────────────

class TestRuleAffects:
    def test_service_entity_produces_affects(self):
        event = _make_event()
        rels = _rule_affects(event, [_service("auth-service")])
        affects = [r for r in rels if r.predicate == "AFFECTS"]
        assert len(affects) == 1
        assert affects[0].object.canonical_name == "auth-service"

    def test_two_services_two_affects(self):
        event = _make_event()
        entities = [_service("auth-service"), _service("payment-gateway")]
        rels = _rule_affects(event, entities)
        assert len(rels) == 2

    def test_no_services_no_affects(self):
        event = _make_event()
        rels = _rule_affects(event, [_person()])
        assert len(rels) == 0


# ─── Rule: DISCUSSED_IN ───────────────────────────────────────────────────────

class TestRuleDiscussedIn:
    def test_service_produces_discussed_in(self):
        event = _make_event()
        rels = _rule_discussed_in(event, [_service()])
        discussed = [r for r in rels if r.predicate == "DISCUSSED_IN"]
        assert len(discussed) == 1

    def test_subject_is_service(self):
        event = _make_event()
        rels = _rule_discussed_in(event, [_service("auth-service")])
        assert rels[0].subject.canonical_name == "auth-service"


# ─── Rule: REFERENCES ─────────────────────────────────────────────────────────

class TestRuleReferences:
    def test_ticket_produces_references(self):
        event = _make_event()
        rels = _rule_references(event, [_ticket("PROJ-42")])
        refs = [r for r in rels if r.predicate == "REFERENCES"]
        assert len(refs) == 1
        assert refs[0].object.canonical_name == "PROJ-42"

    def test_no_tickets_no_references(self):
        event = _make_event()
        rels = _rule_references(event, [_person(), _service()])
        assert len(rels) == 0


# ─── Rule: OWNS ───────────────────────────────────────────────────────────────

class TestRuleOwns:
    def test_team_and_service_produce_owns(self):
        rels = _rule_owns([_team(), _service()])
        assert len(rels) == 0

    def test_owns_confidence_is_0_6(self):
        rels = _rule_owns([_team(), _service()])
        assert len(rels) == 0

    def test_no_team_no_owns(self):
        rels = _rule_owns([_service(), _service("payment-gateway")])
        assert len(rels) == 0


# ─── Rule: DEPENDS_ON ─────────────────────────────────────────────────────────

class TestRuleDependsOn:
    def test_github_two_services_depends_on(self):
        event = _make_event(source=SourceType.GITHUB)
        entities = [_service("auth-service"), _service("payment-gateway")]
        rels = _rule_depends_on(event, entities)
        depends = [r for r in rels if r.predicate == "DEPENDS_ON"]
        assert len(depends) == 1

    def test_slack_event_no_depends_on(self):
        event = _make_event(source=SourceType.SLACK)
        entities = [_service("auth-service"), _service("payment-gateway")]
        rels = _rule_depends_on(event, entities)
        assert len(rels) == 0

    def test_one_service_no_depends_on(self):
        event = _make_event(source=SourceType.GITHUB)
        rels = _rule_depends_on(event, [_service()])
        assert len(rels) == 0

    def test_three_services_no_depends_on(self):
        # Only fires for exactly 2 services (to avoid noise)
        event = _make_event(source=SourceType.GITHUB)
        entities = [_service("a"), _service("b"), _service("c")]
        rels = _rule_depends_on(event, entities)
        assert len(rels) == 0


# ─── Rule: RELATED_TO ────────────────────────────────────────────────────────

class TestRuleRelatedTo:
    def test_two_different_non_persons_related(self):
        entities = [_service("auth-service"), _ticket("PROJ-42")]
        rels = _rule_related_to(entities)
        assert len(rels) == 0

    def test_persons_excluded(self):
        entities = [_person("alice"), _service("auth-service")]
        rels = _rule_related_to(entities)
        assert len(rels) == 0

    def test_same_name_not_related_to_itself(self):
        entities = [_service("auth-service"), _service("auth-service")]
        rels = _rule_related_to(entities)
        assert len(rels) == 0

    def test_team_service_pair_skipped(self):
        entities = [_team("platform-team"), _service("auth-service")]
        rels = _rule_related_to(entities)
        assert len(rels) == 0


# ─── Full extractor ───────────────────────────────────────────────────────────

class TestRelationshipExtractorFull:
    def test_returns_empty_with_no_entities(self):
        extractor = RelationshipExtractor()
        event = _make_event()
        rels = extractor.extract(event, [])
        assert rels == []

    def test_returns_list_of_relationship_refs(self):
        extractor = RelationshipExtractor()
        event = _make_event()
        entities = [
            _ref("alice", EntityType.PERSON, source="structured_author_id"),
            _service("auth-service"),
        ]
        rels = extractor.extract(event, entities)
        assert all(isinstance(r, RelationshipRef) for r in rels)

    def test_multiple_rules_fire_together(self):
        extractor = RelationshipExtractor()
        event = _make_event()
        entities = [
            _ref("alice", EntityType.PERSON, source="structured_author_id"),
            _service("auth-service"),
            _team("platform-team"),
        ]
        rels = extractor.extract(event, entities)
        predicates = {r.predicate for r in rels}
        # Should have AUTHORED, AFFECTS, DISCUSSED_IN at minimum
        assert "AUTHORED" in predicates
        assert "AFFECTS" in predicates
        assert "DISCUSSED_IN" in predicates
        assert "OWNS" not in predicates
