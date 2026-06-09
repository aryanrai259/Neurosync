# Purpose:      Memory models — short-term session context and long-term
#               workspace knowledge snapshots. These are what the reasoning
#               layer reads before constructing an LLM prompt, so the system
#               can answer follow-up questions and remember past decisions.
# Called By:    memory/session_store.py (produces/consumes SessionContext)
#               memory/workspace_memory.py (produces/consumes WorkspaceSnapshot)
#               reasoning/orchestrator.py (reads both before every query)
#               reasoning/composer.py (injects memory into LLM prompt)
# Calls:        models/enums.py (MessageRole)
# Dependencies: pydantic v2, python stdlib (uuid, datetime)
# Test File:    tests/unit/models/test_memory.py

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .enums import MessageRole


class ConversationMessage(BaseModel):
    """
    A single turn in a conversation — one message from user or assistant.

    Stored in order inside SessionContext.messages.
    The role field tells the LLM who said what when building the prompt.
    """

    model_config = ConfigDict(frozen=True)

    role: MessageRole = Field(
        description="Who produced this message: user, assistant, or system.",
    )
    content: str = Field(
        min_length=1,
        description="The text content of this message.",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When this message was produced. Always UTC.",
    )

    @field_validator("content")
    @classmethod
    def content_must_not_be_whitespace_only(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("message content cannot be whitespace-only")
        return v

    @field_validator("timestamp", mode="before")
    @classmethod
    def must_be_timezone_aware(cls, v: Any) -> Any:
        if isinstance(v, datetime) and v.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware")
        return v


class SessionContext(BaseModel):
    """
    Short-term memory for an active conversation session.

    Stored in Redis (fast, TTL-expiring). Each user query reads this first
    so the LLM can answer follow-up questions with full context.

    When messages grows large enough to exceed max_context_tokens,
    the memory/summarizer.py compresses older messages into summary
    and keeps only the most recent messages in the list.
    """

    model_config = ConfigDict(frozen=True)

    session_id: str = Field(
        min_length=1,
        description="Unique session identifier. Returned in QueryResponse and echoed back.",
    )
    workspace_id: UUID = Field(
        description="Which workspace this session belongs to.",
    )
    messages: list[ConversationMessage] = Field(
        default_factory=list,
        description="Ordered list of conversation turns, newest last.",
    )
    summary: str | None = Field(
        default=None,
        description=(
            "Compressed summary of older messages, generated when the context window "
            "would be exceeded. None = all history fits in messages list."
        ),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When this session started.",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When this session last received a message.",
    )

    @field_validator("session_id")
    @classmethod
    def session_id_must_not_be_whitespace_only(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("session_id cannot be whitespace-only")
        return v

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def must_be_timezone_aware(cls, v: Any) -> Any:
        if isinstance(v, datetime) and v.tzinfo is None:
            raise ValueError("datetime must be timezone-aware")
        return v


class WorkspaceSnapshot(BaseModel):
    """
    Long-term memory for a workspace — key facts that persist across sessions.

    Stored in PostgreSQL. Read at the start of every query to give the LLM
    high-level workspace context before it digs into retrieved chunks.

    Updated periodically by the memory/workspace_memory.py module as new
    events are ingested and new decisions are detected.
    """

    model_config = ConfigDict(frozen=True)

    workspace_id: UUID = Field(
        description="Which workspace this snapshot belongs to.",
    )
    key_decisions: list[str] = Field(
        default_factory=list,
        description=(
            "Important decisions made in this workspace, in plain English. "
            "e.g. 'Moved auth session storage to Redis (Q3 2024)'. "
            "Injected into LLM context for every query."
        ),
    )
    active_entities: list[str] = Field(
        default_factory=list,
        description=(
            "Most frequently referenced entity names in recent events. "
            "e.g. ['auth-service', 'Alice Chen', 'payment-api']. "
            "Helps the LLM orient itself to this workspace's domain."
        ),
    )
    summary: str | None = Field(
        default=None,
        description=(
            "High-level summary of this workspace: what the team does, "
            "key projects, technology stack. Generated by LLM from events."
        ),
    )
    event_count: int = Field(
        default=0,
        ge=0,
        description="Total number of events ingested into this workspace.",
    )
    last_ingestion_at: datetime | None = Field(
        default=None,
        description="When the most recent ingestion job completed for this workspace.",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When this snapshot was first created.",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When this snapshot was last refreshed.",
    )

    @field_validator("created_at", "updated_at", "last_ingestion_at", mode="before")
    @classmethod
    def must_be_timezone_aware(cls, v: Any) -> Any:
        if isinstance(v, datetime) and v.tzinfo is None:
            raise ValueError("datetime must be timezone-aware")
        return v
