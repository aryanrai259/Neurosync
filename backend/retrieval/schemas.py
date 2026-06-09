# Purpose:      Retrieval output schemas.
#               RetrievedChunk is the canonical output of any retrieval operation.
#               All retrieval modules (vector, graph, hybrid) return this type.
#               Downstream consumers (reasoning layer, API) depend only on this schema.
# Called By:    retrieval/vector_search.py, retrieval/graph_search.py, retrieval/hybrid.py
# Calls:        models/enums.py (SourceType)
# Dependencies: pydantic v2, python stdlib (uuid, datetime)
# Test File:    tests/unit/retrieval/test_hybrid.py

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from backend.models.enums import SourceType


class RetrievedChunk(BaseModel):
    """
    A single piece of retrieved context from the retrieval layer.

    Produced by vector_search.py and graph_search.py.
    Merged and ranked by hybrid.py.
    Consumed by the reasoning layer (Phase 5+) and the retrieval API.

    Scoring fields:
        vector_score:   Cosine similarity score (0.0–1.0, higher = more similar).
                        0.0 if this chunk was not returned by vector search.
        graph_score:    1.0 if this chunk was returned by graph traversal, else 0.0.
        combined_score: Weighted merge: 0.7 * vector_score + 0.3 * graph_score.
                        Used for final ranking in hybrid.py.
    """

    model_config = ConfigDict(frozen=True)

    event_id: UUID = Field(
        description="FK → events.id. The deduplication key across all retrieval paths.",
    )
    content: str = Field(
        description="The event text content. Used for LLM context injection (Phase 5).",
    )
    title: str | None = Field(
        default=None,
        description="Event title, if available.",
    )
    source: SourceType = Field(
        description="Source system this event originated from.",
    )
    timestamp: datetime = Field(
        description="When this event occurred in the source system.",
    )
    author_id: str = Field(
        description="Author identifier from the source system.",
    )
    url: str | None = Field(
        default=None,
        description="Link back to the original item in the source system.",
    )
    vector_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Cosine similarity score. 0.0 if not from vector search.",
    )
    graph_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Graph traversal score. 1.0 if returned by graph, 0.0 otherwise.",
    )
    combined_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Weighted merge: 0.7 * vector_score + 0.3 * graph_score.",
    )
    entities: list[str] = Field(
        default_factory=list,
        description="Entity canonical names found in this chunk (for context display).",
    )
