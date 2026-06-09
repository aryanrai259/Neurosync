# Purpose:      Unit tests for models/memory.py
#               Tests: ConversationMessage, SessionContext, WorkspaceSnapshot
# Dependencies: pytest, pydantic v2
# Run with:     pytest tests/unit/models/test_memory.py -v --cov=backend

import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from pydantic import ValidationError

from backend.models.enums import MessageRole
from backend.models.memory import ConversationMessage, SessionContext, WorkspaceSnapshot

UTC = timezone.utc
NOW = datetime.now(UTC)


# ─── ConversationMessage ──────────────────────────────────────────────────────

class TestConversationMessage:
    def test_valid_message(self):
        m = ConversationMessage(role=MessageRole.USER, content="What is Redis?")
        assert m.role == MessageRole.USER
        assert m.content == "What is Redis?"

    def test_missing_role_raises(self):
        with pytest.raises(ValidationError):
            ConversationMessage(content="Hello")

    def test_missing_content_raises(self):
        with pytest.raises(ValidationError):
            ConversationMessage(role=MessageRole.USER)

    def test_whitespace_only_content_raises(self):
        with pytest.raises(ValidationError, match="whitespace-only"):
            ConversationMessage(role=MessageRole.USER, content="   ")

    def test_tab_only_content_raises(self):
        with pytest.raises(ValidationError):
            ConversationMessage(role=MessageRole.USER, content="\t")

    def test_empty_content_raises(self):
        with pytest.raises(ValidationError):
            ConversationMessage(role=MessageRole.USER, content="")

    def test_timestamp_defaults_to_utc(self):
        m = ConversationMessage(role=MessageRole.ASSISTANT, content="Answer.")
        assert m.timestamp.tzinfo == UTC

    def test_naive_timestamp_raises(self):
        with pytest.raises(ValidationError, match="timezone-aware"):
            ConversationMessage(
                role=MessageRole.USER,
                content="Hi",
                timestamp=datetime(2024, 1, 1),
            )

    def test_message_is_frozen(self):
        m = ConversationMessage(role=MessageRole.USER, content="Hi")
        with pytest.raises(ValidationError):
            m.content = "changed"  # type: ignore

    @pytest.mark.parametrize("role", list(MessageRole))
    def test_all_roles_accepted(self, role: MessageRole):
        m = ConversationMessage(role=role, content="Some content.")
        assert m.role == role

    def test_non_utc_timezone_accepted(self):
        tz_ist = timezone(timedelta(hours=5, minutes=30))
        ts = datetime(2024, 6, 1, 12, 0, tzinfo=tz_ist)
        m = ConversationMessage(role=MessageRole.USER, content="Hi", timestamp=ts)
        assert m.timestamp.tzinfo == tz_ist


# ─── SessionContext ───────────────────────────────────────────────────────────

class TestSessionContext:
    def _make(self, **kwargs) -> SessionContext:
        defaults = dict(session_id="session-abc-123", workspace_id=uuid4())
        return SessionContext(**{**defaults, **kwargs})

    def test_missing_session_id_raises(self):
        with pytest.raises(ValidationError):
            SessionContext(workspace_id=uuid4())

    def test_missing_workspace_id_raises(self):
        with pytest.raises(ValidationError):
            SessionContext(session_id="sess-1")

    def test_messages_empty_by_default(self):
        assert self._make().messages == []

    def test_summary_none_by_default(self):
        assert self._make().summary is None

    def test_created_at_is_utc(self):
        assert self._make().created_at.tzinfo == UTC

    def test_updated_at_is_utc(self):
        assert self._make().updated_at.tzinfo == UTC

    def test_whitespace_only_session_id_raises(self):
        with pytest.raises(ValidationError, match="whitespace-only"):
            self._make(session_id="   ")

    def test_empty_session_id_raises(self):
        with pytest.raises(ValidationError):
            self._make(session_id="")

    def test_naive_created_at_raises(self):
        with pytest.raises(ValidationError, match="timezone-aware"):
            self._make(created_at=datetime(2024, 1, 1))

    def test_naive_updated_at_raises(self):
        with pytest.raises(ValidationError, match="timezone-aware"):
            self._make(updated_at=datetime(2024, 1, 1))

    def test_explicit_aware_datetime_accepted(self):
        ts = datetime(2024, 6, 1, tzinfo=UTC)
        ctx = self._make(created_at=ts, updated_at=ts)
        assert ctx.created_at == ts

    def test_messages_can_be_set(self):
        msgs = [
            ConversationMessage(role=MessageRole.USER, content="Why Redis?"),
            ConversationMessage(role=MessageRole.ASSISTANT, content="For scalability."),
        ]
        ctx = self._make(messages=msgs)
        assert len(ctx.messages) == 2
        assert ctx.messages[0].role == MessageRole.USER

    def test_summary_can_be_set(self):
        ctx = self._make(summary="User asked about auth decisions.")
        assert ctx.summary == "User asked about auth decisions."

    def test_context_is_frozen(self):
        ctx = self._make()
        with pytest.raises(ValidationError):
            ctx.session_id = "other"  # type: ignore

    def test_model_copy_adds_message(self):
        ctx = self._make()
        msg = ConversationMessage(role=MessageRole.USER, content="Follow up?")
        updated = ctx.model_copy(update={"messages": [*ctx.messages, msg]})
        assert len(updated.messages) == 1
        assert len(ctx.messages) == 0  # original unchanged


# ─── WorkspaceSnapshot ────────────────────────────────────────────────────────

class TestWorkspaceSnapshot:
    def _make(self, **kwargs) -> WorkspaceSnapshot:
        defaults = dict(workspace_id=uuid4())
        return WorkspaceSnapshot(**{**defaults, **kwargs})

    def test_missing_workspace_id_raises(self):
        with pytest.raises(ValidationError):
            WorkspaceSnapshot()

    def test_key_decisions_empty_by_default(self):
        assert self._make().key_decisions == []

    def test_active_entities_empty_by_default(self):
        assert self._make().active_entities == []

    def test_summary_none_by_default(self):
        assert self._make().summary is None

    def test_event_count_zero_by_default(self):
        assert self._make().event_count == 0

    def test_last_ingestion_at_none_by_default(self):
        assert self._make().last_ingestion_at is None

    def test_created_at_is_utc(self):
        assert self._make().created_at.tzinfo == UTC

    def test_updated_at_is_utc(self):
        assert self._make().updated_at.tzinfo == UTC

    def test_event_count_negative_raises(self):
        with pytest.raises(ValidationError):
            self._make(event_count=-1)

    def test_event_count_zero_valid(self):
        assert self._make(event_count=0).event_count == 0

    def test_naive_created_at_raises(self):
        with pytest.raises(ValidationError, match="timezone-aware"):
            self._make(created_at=datetime(2024, 1, 1))

    def test_naive_updated_at_raises(self):
        with pytest.raises(ValidationError, match="timezone-aware"):
            self._make(updated_at=datetime(2024, 1, 1))

    def test_naive_last_ingestion_at_raises(self):
        with pytest.raises(ValidationError, match="timezone-aware"):
            self._make(last_ingestion_at=datetime(2024, 1, 1))

    def test_aware_last_ingestion_at_accepted(self):
        ts = datetime(2024, 6, 1, tzinfo=UTC)
        snap = self._make(last_ingestion_at=ts)
        assert snap.last_ingestion_at == ts

    def test_key_decisions_can_be_set(self):
        decisions = ["Moved auth to Redis (Q3 2024)", "Adopted GraphQL for API (Q1 2024)"]
        snap = self._make(key_decisions=decisions)
        assert snap.key_decisions == decisions

    def test_active_entities_can_be_set(self):
        entities = ["auth-service", "Alice Chen", "payment-api"]
        snap = self._make(active_entities=entities)
        assert snap.active_entities == entities

    def test_summary_can_be_set(self):
        snap = self._make(summary="Platform team at Acme Corp, focused on auth.")
        assert snap.summary == "Platform team at Acme Corp, focused on auth."

    def test_snapshot_is_frozen(self):
        snap = self._make()
        with pytest.raises(ValidationError):
            snap.event_count = 5  # type: ignore

    def test_model_copy_increments_event_count(self):
        snap = self._make(event_count=100)
        updated = snap.model_copy(update={"event_count": 101})
        assert updated.event_count == 101
        assert snap.event_count == 100


# ─── MessageRole enum ─────────────────────────────────────────────────────────

class TestMessageRoleEnum:
    def test_all_expected_values_exist(self):
        values = {e.value for e in MessageRole}
        assert values == {"user", "assistant", "system"}

    def test_role_is_string(self):
        assert isinstance(MessageRole.USER, str)
        assert MessageRole.USER == "user"
