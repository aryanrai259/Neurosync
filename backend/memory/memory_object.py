# Purpose:      MemoryObject — the canonical in-memory result of Phase 4A construction.
#               Produced by memory/memory_constructor.py from a NormalizedEvent.
#               Consumed by memory/vector_indexer.py (Phase 4B) and
#               graph/writer.py (Phase 4C).
#               Never persisted as-is. Its extraction results are stored
#               in the memory_objects table as JSON for replay/debugging.
# Called By:    memory/memory_constructor.py (produces)
#               memory/vector_indexer.py (consumes)
#               graph/writer.py (consumes)
# Calls:        models/enums.py (SourceType, EntityType)
# Dependencies: pydantic v2, python stdlib (uuid, datetime)
# Test File:    tests/unit/memory/test_memory_object.py

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from backend.models.enums import EntityType, SourceType


class EntityRef(BaseModel):
    """
    A resolved entity reference — one node in the graph-to-be.

    canonical_name is always normalised to lowercase stripped form.
    confidence reflects the extraction tier: 1.0 for exact match,
    0.85 for pattern match, 0.6 for co-occurrence inference.
    extraction_source is the name of the rule that produced this ref,
    kept for full provenance on every downstream edge.
    """

    model_config = ConfigDict(frozen=True)

    canonical_name: str = Field(
        min_length=1,
        description="Normalised, lowercased canonical name. e.g. 'auth-service', 'alice'.",
    )
    entity_type: EntityType = Field(
        description="Category of this entity.",
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Extraction confidence. 1.0=exact, 0.85=pattern, 0.6=co-occurrence.",
    )
    extraction_source: str = Field(
        description=(
            "Name of the rule that produced this ref. "
            "e.g. 'structured_github_author', 'seed_list_service', 'pattern_ticket'."
        ),
    )


class RelationshipRef(BaseModel):
    """
    A directed relationship between two EntityRefs — one edge in the graph-to-be.

    predicate is one of the seven canonical relationship types.
    confidence and extraction_source carry full provenance so that when
    the edge is written to Neo4j it retains its lineage.
    """

    model_config = ConfigDict(frozen=True)

    subject: EntityRef = Field(description="The 'from' node of this relationship.")
    predicate: Literal[
        "AUTHORED",
        "OWNS",
        "DEPENDS_ON",
        "REFERENCES",
        "DISCUSSED_IN",
        "AFFECTS",
        "RELATED_TO",
    ] = Field(description="Relationship type. One of the seven canonical predicates.")
    object: EntityRef = Field(description="The 'to' node of this relationship.")
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Relationship confidence, derived from the weaker of subject/object.",
    )
    extraction_source: str = Field(
        description="Name of the rule that generated this relationship.",
    )


class MemoryObject(BaseModel):
    """
    The canonical Phase 4A construction artifact.

    One MemoryObject is produced per NormalizedEvent. It carries the event's
    content plus all entities and relationships extracted from it, ready for:
      - Persistence to memory_objects table (replay log)
      - Embedding into PgVector via vector_indexer.py (Phase 4B)
      - Graph upsert into Neo4j via graph/writer.py (Phase 4C)

    Key invariants:
    - event_id is always set and non-null. It is the provenance anchor.
    - entities and relationships are empty lists when nothing was extracted —
      never None. This avoids None checks in downstream consumers.
    - content is exactly NormalizedEvent.content — no modification.
      This is what gets embedded in Phase 4B.
    - This model is frozen. Downstream consumers must not mutate it.
    """

    model_config = ConfigDict(frozen=True)

    event_id: UUID = Field(
        description="FK → events.id. The provenance anchor for this memory object.",
    )
    workspace_id: UUID = Field(
        description="Workspace this memory object belongs to.",
    )
    source: SourceType = Field(
        description="Source system this event originated from.",
    )
    content: str = Field(
        min_length=1,
        description="Verbatim event content. Embedded in Phase 4B.",
    )
    title: str | None = Field(
        default=None,
        description="Optional title from the normalized event.",
    )
    author_id: str = Field(
        min_length=1,
        description="Author identifier from the source system.",
    )
    timestamp: datetime = Field(
        description="When this event occurred in the source system.",
    )
    entities: list[EntityRef] = Field(
        default_factory=list,
        description="All entities resolved from this event. Empty list if none found.",
    )
    relationships: list[RelationshipRef] = Field(
        default_factory=list,
        description="All relationships extracted from this event. Empty list if none found.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Passthrough of NormalizedEvent.metadata for downstream context.",
    )
