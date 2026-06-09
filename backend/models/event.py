# Purpose:      Canonical event model — the normalised form of any piece of
#               data ingested from any source. This is the most central type
#               in Company Brain. Every downstream system consumes this shape.
# Called By:    ingestion/ (produces events), retrieval/ (queries events),
#               graph/ (extracts entities from events), reasoning/ (reads events),
#               models/entity.py, models/ingestion.py
# Calls:        models/enums.py (SourceType)
# Dependencies: pydantic v2, python stdlib (uuid, datetime, typing)
# Test File:    tests/unit/models/test_event.py

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


from .enums import EmbeddingStatus, SourceType


class NormalizedEvent(BaseModel):
    """
    The canonical representation of any ingested event.

    Regardless of whether the original data came from Slack, GitHub, Jira,
    Notion, or email — it lands in this shape before being stored, embedded,
    or added to the graph.

    Key design decisions:
    - source_id: the original ID from the source system (Slack ts, GitHub SHA,
      Jira key). Used for deduplication — upserting on (source, source_id)
      prevents double-ingestion if the same event arrives twice.
    - content: the normalised text that gets embedded into the vector store.
      Kept separate from metadata so embedding is always deterministic.
    - embedding_status: Tracks whether the event has been chunked and vectorized.
      One event may generate multiple chunks, so we just track status here rather
      than storing a single embedding_id.
    - timestamp vs created_at: timestamp = when it happened in the source
      system. created_at = when Company Brain ingested it. Both matter for
      temporal queries.
    """

    model_config = ConfigDict(frozen=True)

    id: UUID = Field(
        default_factory=uuid4,
        description="Company Brain internal ID. Source systems use their own IDs.",
    )
    source: SourceType = Field(
        description="Which system this event came from.",
    )
    workspace_id: UUID = Field(
        description="Workspace this event belongs to. All queries are scoped by this.",
    )
    source_id: str = Field(
        min_length=1,
        description=(
            "Original ID in the source system "
            "(Slack message ts, GitHub commit SHA, Jira ticket key). "
            "Used for deduplication: upsert on (source, workspace_id, source_id)."
        ),
    )
    content: str = Field(
        min_length=1,
        description="Normalised text content. This is what gets embedded into the vector store.",
    )
    title: str | None = Field(
        default=None,
        description="Optional title — PR title, ticket summary, document name.",
    )
    author_id: str = Field(
        min_length=1,
        description="Author's identifier in the source system.",
    )
    author_name: str | None = Field(
        default=None,
        description="Author display name if the source provides it.",
    )
    url: str | None = Field(
        default=None,
        description="Link back to the original item in the source system.",
    )
    timestamp: datetime = Field(
        description="When this event occurred in the source system. Must be timezone-aware.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Source-specific extra fields that don't fit the canonical schema. "
            "Examples: thread_id (Slack), pr_number (GitHub), labels (Jira)."
        ),
    )
    embedding_status: EmbeddingStatus = Field(
        default=EmbeddingStatus.PENDING,
        description=(
            "Status of vectorization. "
            "PENDING means the async pipeline needs to process this event. "
            "One event may generate multiple vector chunks."
        ),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When Company Brain ingested this event. Always UTC.",
    )

    @field_validator("timestamp", "created_at", mode="before")
    @classmethod
    def must_be_timezone_aware(cls, v: Any) -> Any:
        """Reject naive datetimes — all timestamps must be timezone-aware."""
        if isinstance(v, datetime) and v.tzinfo is None:
            raise ValueError(
                "datetime must be timezone-aware. "
                "Use datetime.now(timezone.utc) or attach tzinfo explicitly."
            )
        return v

    @field_validator("content")
    @classmethod
    def content_must_not_be_whitespace_only(cls, v: str) -> str:
        """Prevent whitespace-only strings from being embedded."""
        if not v.strip():
            raise ValueError("content cannot be whitespace-only")
        return v
