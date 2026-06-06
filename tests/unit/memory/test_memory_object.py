# Purpose:      Unit tests for memory/memory_object.py
# Tests:        MemoryObject, EntityRef, RelationshipRef — schema validation,
#               defaults, immutability, required fields.
# Run with:     pytest tests/unit/memory/test_memory_object.py -v

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from backend.memory.memory_object import EntityRef, MemoryObject, RelationshipRef
from backend.models.enums import EntityType, SourceType


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _make_ref(**kwargs) -> EntityRef:
    defaults = dict(
        canonical_name="auth-service",
        entity_type=EntityType.SERVICE,
        confidence=1.0,
        extraction_source="seed_list_service",
    )
    return EntityRef(**{**defaults, **kwargs})


def _make_memory_object(**kwargs) -> MemoryObject:
    defaults = dict(
        event_id=uuid4(),
        workspace_id=uuid4(),
        source=SourceType.GITHUB,
        content="PR: fix auth-service login bug",
        author_id="alice",
        timestamp=datetime.now(timezone.utc),
    )
    return MemoryObject(**{**defaults, **kwargs})


# ─── EntityRef ────────────────────────────────────────────────────────────────

class TestEntityRef:
    def test_valid_entity_ref(self):
        ref = _make_ref()
        assert ref.canonical_name == "auth-service"
        assert ref.entity_type == EntityType.SERVICE
        assert ref.confidence == 1.0

    def test_empty_canonical_name_raises(self):
        with pytest.raises(ValidationError):
            _make_ref(canonical_name="")

    def test_confidence_above_1_raises(self):
        with pytest.raises(ValidationError):
            _make_ref(confidence=1.01)

    def test_confidence_below_0_raises(self):
        with pytest.raises(ValidationError):
            _make_ref(confidence=-0.1)

    def test_frozen_raises_on_mutation(self):
        ref = _make_ref()
        with pytest.raises(ValidationError):
            ref.confidence = 0.5  # type: ignore

    def test_all_entity_types_accepted(self):
        for et in EntityType:
            ref = _make_ref(entity_type=et)
            assert ref.entity_type == et


# ─── RelationshipRef ──────────────────────────────────────────────────────────

class TestRelationshipRef:
    def _make_rel(self, predicate="AUTHORED", **kwargs) -> RelationshipRef:
        subject = _make_ref(canonical_name="alice", entity_type=EntityType.PERSON)
        obj = _make_ref(canonical_name="auth-service", entity_type=EntityType.SERVICE)
        return RelationshipRef(
            subject=subject,
            predicate=predicate,
            object=obj,
            confidence=1.0,
            extraction_source="rule_authored_structured",
            **kwargs,
        )

    def test_valid_relationship(self):
        rel = self._make_rel()
        assert rel.predicate == "AUTHORED"
        assert rel.subject.canonical_name == "alice"

    def test_invalid_predicate_raises(self):
        with pytest.raises(ValidationError):
            self._make_rel(predicate="INVENTED")

    def test_all_valid_predicates(self):
        valid_predicates = [
            "AUTHORED", "OWNS", "DEPENDS_ON", "REFERENCES",
            "DISCUSSED_IN", "AFFECTS", "RELATED_TO",
        ]
        for pred in valid_predicates:
            rel = self._make_rel(predicate=pred)
            assert rel.predicate == pred

    def test_frozen_raises_on_mutation(self):
        rel = self._make_rel()
        with pytest.raises(ValidationError):
            rel.predicate = "OWNS"  # type: ignore


# ─── MemoryObject ─────────────────────────────────────────────────────────────

class TestMemoryObject:
    def test_valid_memory_object(self):
        mo = _make_memory_object()
        assert mo.entities == []
        assert mo.relationships == []
        assert mo.metadata == {}
        assert mo.title is None

    def test_event_id_is_required(self):
        with pytest.raises(ValidationError):
            MemoryObject(
                workspace_id=uuid4(),
                source=SourceType.GITHUB,
                content="test",
                author_id="alice",
                timestamp=datetime.now(timezone.utc),
            )

    def test_content_cannot_be_empty(self):
        with pytest.raises(ValidationError):
            _make_memory_object(content="")

    def test_entities_can_be_set(self):
        refs = [_make_ref(), _make_ref(canonical_name="payment-gateway")]
        mo = _make_memory_object(entities=refs)
        assert len(mo.entities) == 2

    def test_frozen_memory_object(self):
        mo = _make_memory_object()
        with pytest.raises(ValidationError):
            mo.content = "changed"  # type: ignore

    def test_metadata_passthrough(self):
        meta = {"pr_number": 42, "labels": ["bug"]}
        mo = _make_memory_object(metadata=meta)
        assert mo.metadata["pr_number"] == 42
