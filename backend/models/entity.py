# Purpose:      Canonical entity model — a named thing extracted from events.
#               Entities become nodes in the Neo4j knowledge graph.
#               Without entities, Company Brain can only do vector search.
#               With entities, it can answer relationship questions:
#               "Who worked on auth?", "What decisions involved Redis?"
# Called By:    graph/entity_extractor.py (produces entities)
#               graph/transformer.py (writes to Neo4j)
#               retrieval/graph_retriever.py (reads from Neo4j)
#               models/query.py (RetrievedChunk references entities)
# Calls:        models/enums.py (EntityType)
# Dependencies: pydantic v2, python stdlib (uuid, datetime, typing)
# Test File:    tests/unit/models/test_entity.py

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .enums import EntityType


class Entity(BaseModel):
    """
    A named entity extracted from one or more NormalizedEvents.

    Entities are the nodes of the knowledge graph. Relationships between
    entities (AUTHORED, DISCUSSED, DECIDED, DEPENDS_ON) are stored as
    edges in Neo4j — but this model only represents the node itself.

    Key design decisions:

    - aliases: The same person can appear as "Alice", "@alice",
      "alice.chen@company.com" across sources. Aliases let the graph
      merge these into one node rather than creating duplicates.

    - source_event_ids: Links back to every NormalizedEvent that mentions
      this entity. This is the bridge between the graph (Neo4j) and the
      vector store (ChromaDB) — a graph traversal yields entity IDs,
      which map to event IDs, which map to vector embeddings.

    - confidence: LLM/NER extraction is imperfect. Low-confidence entities
      (< 0.7) are stored but filtered during retrieval. Over time, human
      confirmation or repeated mentions raise confidence.

    - frozen=True: Entities are treated as immutable value objects.
      To update (add alias, add event reference), use:
          entity.model_copy(update={"aliases": [*entity.aliases, "new-alias"]})
      This keeps the model predictable and thread-safe.
    """

    model_config = ConfigDict(frozen=True)

    id: UUID = Field(
        default_factory=uuid4,
        description="Company Brain internal ID. Maps to the Neo4j node ID.",
    )
    workspace_id: UUID = Field(
        description="Workspace this entity belongs to. All graph queries are scoped here.",
    )
    type: EntityType = Field(
        description="What category of thing this entity is.",
    )
    name: str = Field(
        min_length=1,
        description=(
            "Canonical name for this entity. "
            "e.g. 'Alice Chen', 'auth-service', 'PROJ-1234', 'Redis'."
        ),
    )
    aliases: list[str] = Field(
        default_factory=list,
        description=(
            "Other names this entity is known by across sources. "
            "e.g. ['alice', '@alice', 'alice.chen@company.com']. "
            "Used during graph merging to avoid duplicate nodes."
        ),
    )
    source_event_ids: list[UUID] = Field(
        default_factory=list,
        description=(
            "IDs of NormalizedEvents that mention this entity. "
            "Bridge between the knowledge graph and the vector store."
        ),
    )
    description: str | None = Field(
        default=None,
        description="Optional human-readable summary of who or what this entity is.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Type-specific extra fields. "
            "Examples: github_username (PERSON), repo_url (REPOSITORY), "
            "jira_key (TICKET), status (DECISION)."
        ),
    )
    confidence: float = Field(
        default=1.0,
        description=(
            "Extraction confidence score in range [0.0, 1.0]. "
            "1.0 = manually confirmed. "
            "< 0.7 = filtered out during retrieval by default."
        ),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When this entity was first extracted. Always UTC.",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When this entity was last updated (new alias, new event). Always UTC.",
    )

    @field_validator("name")
    @classmethod
    def name_must_not_be_whitespace_only(cls, v: str) -> str:
        """An entity name must have actual content — not just spaces."""
        if not v.strip():
            raise ValueError("entity name cannot be whitespace-only")
        return v

    @field_validator("confidence")
    @classmethod
    def confidence_must_be_in_range(cls, v: float) -> float:
        """Confidence must be a probability: 0.0 (impossible) to 1.0 (certain)."""
        if not 0.0 <= v <= 1.0:
            raise ValueError(
                f"confidence must be between 0.0 and 1.0, got {v}"
            )
        return v

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def must_be_timezone_aware(cls, v: Any) -> Any:
        """Reject naive datetimes — all timestamps must be timezone-aware."""
        if isinstance(v, datetime) and v.tzinfo is None:
            raise ValueError(
                "datetime must be timezone-aware. "
                "Use datetime.now(timezone.utc) or attach tzinfo explicitly."
            )
        return v
