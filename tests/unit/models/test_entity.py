# Purpose:      Unit tests for models/entity.py — Entity
# Tests:        Field defaults, required fields, all validator branches,
#               confidence range edges, name whitespace, datetime awareness,
#               immutability, model_copy update pattern, all EntityTypes
# Dependencies: pytest, pydantic v2
# Run with:     pytest tests/unit/models/test_entity.py -v --cov=backend/models/entity

import pytest
from datetime import datetime, timezone, timedelta
from uuid import UUID, uuid4

from pydantic import ValidationError

from backend.models.entity import Entity
from backend.models.enums import EntityType


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _make(**kwargs) -> Entity:
    """Build a valid Entity with sensible defaults for any omitted field."""
    defaults = dict(
        workspace_id=uuid4(),
        type=EntityType.PERSON,
        name="Alice Chen",
    )
    return Entity(**{**defaults, **kwargs})


# ─── Required fields ──────────────────────────────────────────────────────────


class TestRequiredFields:
    def test_missing_workspace_id_raises(self):
        with pytest.raises(ValidationError):
            Entity(type=EntityType.PERSON, name="Alice")

    def test_missing_type_raises(self):
        with pytest.raises(ValidationError):
            Entity(workspace_id=uuid4(), name="Alice")

    def test_missing_name_raises(self):
        with pytest.raises(ValidationError):
            Entity(workspace_id=uuid4(), type=EntityType.PERSON)


# ─── Default values ───────────────────────────────────────────────────────────


class TestDefaults:
    def test_id_is_uuid(self):
        assert isinstance(_make().id, UUID)

    def test_each_entity_gets_unique_id(self):
        assert _make().id != _make().id

    def test_aliases_empty_by_default(self):
        assert _make().aliases == []

    def test_source_event_ids_empty_by_default(self):
        assert _make().source_event_ids == []

    def test_description_none_by_default(self):
        assert _make().description is None

    def test_metadata_empty_dict_by_default(self):
        assert _make().metadata == {}

    def test_confidence_is_1_by_default(self):
        assert _make().confidence == 1.0

    def test_created_at_is_utc(self):
        assert _make().created_at.tzinfo == timezone.utc

    def test_updated_at_is_utc(self):
        assert _make().updated_at.tzinfo == timezone.utc


# ─── name validator ───────────────────────────────────────────────────────────


class TestNameValidator:
    def test_valid_name_is_accepted(self):
        assert _make(name="auth-service").name == "auth-service"

    def test_whitespace_only_name_raises(self):
        with pytest.raises(ValidationError, match="whitespace-only"):
            _make(name="   ")

    def test_tab_only_name_raises(self):
        with pytest.raises(ValidationError):
            _make(name="\t")

    def test_newline_only_name_raises(self):
        with pytest.raises(ValidationError):
            _make(name="\n")

    def test_empty_name_raises(self):
        with pytest.raises(ValidationError):
            _make(name="")

    def test_name_with_leading_trailing_spaces_is_accepted(self):
        # Whitespace-padded names are valid — only pure whitespace is rejected
        entity = _make(name="  auth-service  ")
        assert entity.name == "  auth-service  "


# ─── confidence validator ─────────────────────────────────────────────────────


class TestConfidenceValidator:
    def test_confidence_zero_is_valid(self):
        assert _make(confidence=0.0).confidence == 0.0

    def test_confidence_one_is_valid(self):
        assert _make(confidence=1.0).confidence == 1.0

    def test_confidence_midpoint_is_valid(self):
        assert _make(confidence=0.5).confidence == 0.5

    def test_confidence_above_1_raises(self):
        with pytest.raises(ValidationError, match="0.0 and 1.0"):
            _make(confidence=1.01)

    def test_confidence_below_0_raises(self):
        with pytest.raises(ValidationError, match="0.0 and 1.0"):
            _make(confidence=-0.01)

    def test_confidence_well_above_1_raises(self):
        with pytest.raises(ValidationError):
            _make(confidence=2.0)

    def test_confidence_well_below_0_raises(self):
        with pytest.raises(ValidationError):
            _make(confidence=-1.0)

    def test_high_confidence_typical_value(self):
        assert _make(confidence=0.95).confidence == 0.95

    def test_low_confidence_typical_value(self):
        assert _make(confidence=0.42).confidence == 0.42


# ─── datetime validators ──────────────────────────────────────────────────────


class TestDatetimeValidators:
    def test_aware_created_at_is_accepted(self):
        ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
        assert _make(created_at=ts).created_at == ts

    def test_naive_created_at_raises(self):
        with pytest.raises(ValidationError, match="timezone-aware"):
            _make(created_at=datetime(2024, 1, 1))

    def test_aware_updated_at_is_accepted(self):
        ts = datetime(2024, 6, 1, tzinfo=timezone.utc)
        assert _make(updated_at=ts).updated_at == ts

    def test_naive_updated_at_raises(self):
        with pytest.raises(ValidationError, match="timezone-aware"):
            _make(updated_at=datetime(2024, 6, 1))

    def test_non_utc_timezone_is_accepted(self):
        tz_ist = timezone(timedelta(hours=5, minutes=30))
        ts = datetime(2024, 6, 1, 12, 0, tzinfo=tz_ist)
        entity = _make(created_at=ts)
        assert entity.created_at.tzinfo == tz_ist


# ─── Optional fields ──────────────────────────────────────────────────────────


class TestOptionalFields:
    def test_aliases_can_be_set(self):
        aliases = ["alice", "@alice", "alice.chen@company.com"]
        entity = _make(aliases=aliases)
        assert entity.aliases == aliases

    def test_source_event_ids_can_be_set(self):
        ids = [uuid4(), uuid4()]
        entity = _make(source_event_ids=ids)
        assert entity.source_event_ids == ids

    def test_description_can_be_set(self):
        entity = _make(description="Senior engineer on the auth team.")
        assert entity.description == "Senior engineer on the auth team."

    def test_metadata_can_hold_arbitrary_data(self):
        meta = {"github_username": "alice-chen", "team": "platform"}
        entity = _make(metadata=meta)
        assert entity.metadata["github_username"] == "alice-chen"

    def test_metadata_can_be_nested(self):
        meta = {"jira": {"key": "PROJ-1234", "labels": ["bug", "p1"]}}
        entity = _make(metadata=meta)
        assert entity.metadata["jira"]["labels"] == ["bug", "p1"]


# ─── Immutability and model_copy update pattern ───────────────────────────────


class TestImmutabilityAndUpdate:
    def test_entity_is_frozen(self):
        entity = _make()
        with pytest.raises(ValidationError):
            entity.name = "Bob"  # type: ignore

    def test_confidence_cannot_be_mutated(self):
        entity = _make()
        with pytest.raises(ValidationError):
            entity.confidence = 0.5  # type: ignore

    def test_model_copy_with_new_alias(self):
        entity = _make(aliases=["alice"])
        updated = entity.model_copy(
            update={"aliases": [*entity.aliases, "@alice"]}
        )
        assert updated.aliases == ["alice", "@alice"]
        assert entity.aliases == ["alice"]  # original unchanged

    def test_model_copy_with_new_source_event_id(self):
        event_id = uuid4()
        entity = _make()
        updated = entity.model_copy(
            update={"source_event_ids": [event_id]}
        )
        assert event_id in updated.source_event_ids
        assert entity.source_event_ids == []  # original unchanged

    def test_model_copy_with_updated_confidence(self):
        entity = _make(confidence=0.6)
        updated = entity.model_copy(update={"confidence": 0.9})
        assert updated.confidence == 0.9
        assert entity.confidence == 0.6


# ─── All entity types ─────────────────────────────────────────────────────────


class TestAllEntityTypes:
    @pytest.mark.parametrize("entity_type", list(EntityType))
    def test_all_entity_types_accepted(self, entity_type: EntityType):
        entity = _make(type=entity_type)
        assert entity.type == entity_type

    def test_invalid_entity_type_raises(self):
        with pytest.raises(ValidationError):
            _make(type="unknown_type")  # type: ignore


# ─── Workspace scoping ────────────────────────────────────────────────────────


class TestWorkspaceScoping:
    def test_workspace_id_is_uuid(self):
        ws_id = uuid4()
        entity = _make(workspace_id=ws_id)
        assert entity.workspace_id == ws_id

    def test_two_entities_can_share_workspace_id(self):
        ws_id = uuid4()
        e1 = _make(workspace_id=ws_id, name="Alice")
        e2 = _make(workspace_id=ws_id, name="Bob")
        assert e1.workspace_id == e2.workspace_id
        assert e1.id != e2.id
