# Purpose:      API contract for the query endpoint — defines what enters and
#               leaves Company Brain when a user asks a question.
#               Also defines RetrievedChunk: the unit of context the reasoning
#               layer pulls from storage and passes to the LLM.
# Called By:    api/query.py (uses QueryRequest, QueryResponse)
#               reasoning/composer.py (produces QueryResponse)
#               retrieval/ (produces List[RetrievedChunk])
# Calls:        models/enums.py (SourceType, RetrievalStrategy)
# Dependencies: pydantic v2, python stdlib (uuid, datetime, typing)
# Test File:    tests/unit/models/test_query.py

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .enums import RetrievalStrategy, SourceType


class QueryFilters(BaseModel):
    """
    Optional filters to narrow the retrieval scope.

    All fields are optional. Unset fields apply no filtering.
    Embedded inside QueryRequest — not a standalone API type.
    """

    model_config = ConfigDict(frozen=True)

    sources: list[SourceType] | None = Field(
        default=None,
        description="Restrict retrieval to specific source systems. None = all sources.",
    )
    time_from: datetime | None = Field(
        default=None,
        description="Only retrieve events at or after this timestamp. Must be timezone-aware.",
    )
    time_to: datetime | None = Field(
        default=None,
        description="Only retrieve events at or before this timestamp. Must be timezone-aware.",
    )
    author_ids: list[str] | None = Field(
        default=None,
        description="Restrict retrieval to events authored by these source-system user IDs.",
    )

    @field_validator("time_from", "time_to", mode="before")
    @classmethod
    def must_be_timezone_aware(cls, v: Any) -> Any:
        """Reject naive datetimes in filter timestamps."""
        if isinstance(v, datetime) and v.tzinfo is None:
            raise ValueError("filter datetime must be timezone-aware")
        return v

    @model_validator(mode="after")
    def time_range_must_be_valid(self) -> "QueryFilters":
        """time_from must come before time_to when both are provided."""
        if self.time_from is not None and self.time_to is not None:
            if self.time_from >= self.time_to:
                raise ValueError("time_from must be before time_to")
        return self


class QueryRequest(BaseModel):
    """
    Payload for POST /query — what the client sends when asking a question.

    All retrieval behaviour is controlled from here:
    which workspace to search, which strategy to use, how many results,
    and any narrowing filters.
    """

    model_config = ConfigDict(frozen=True)

    query: str = Field(
        min_length=1,
        description="The natural language question from the user.",
    )
    workspace_id: UUID = Field(
        description="Which workspace to search. All retrieval is scoped to this.",
    )
    session_id: str | None = Field(
        default=None,
        description=(
            "Conversation session ID for multi-turn queries. "
            "None = start a new session. "
            "Provide the value returned in the previous QueryResponse to continue."
        ),
    )
    strategy: RetrievalStrategy = Field(
        default=RetrievalStrategy.HYBRID,
        description="Retrieval strategy: vector | graph | hybrid (default).",
    )
    max_results: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of chunks to retrieve (1–50).",
    )
    min_confidence: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description=(
            "Minimum entity confidence score for graph retrieval (0.0–1.0). "
            "Entities below this threshold are excluded from graph traversal."
        ),
    )
    filters: QueryFilters | None = Field(
        default=None,
        description="Optional filters to narrow retrieval by source, time, or author.",
    )

    @field_validator("query")
    @classmethod
    def query_must_not_be_whitespace_only(cls, v: str) -> str:
        """A query must contain actual content to retrieve against."""
        if not v.strip():
            raise ValueError("query cannot be whitespace-only")
        return v


class RetrievedChunk(BaseModel):
    """
    One piece of context retrieved from storage in response to a query.

    This is the unit the reasoning layer passes to the LLM as context,
    and what the frontend shows as source citations in the answer UI.

    score reflects how relevant this chunk was to the original query —
    used for display ordering and answer confidence calculation.
    """

    model_config = ConfigDict(frozen=True)

    event_id: UUID = Field(
        description="ID of the NormalizedEvent this chunk came from. Traceable back to source.",
    )
    content: str = Field(
        min_length=1,
        description="The text content shown to the LLM and returned as a source citation.",
    )
    source: SourceType = Field(
        description="Which system this content came from.",
    )
    source_id: str = Field(
        min_length=1,
        description="Original ID in the source system.",
    )
    title: str | None = Field(
        default=None,
        description="Optional title — PR title, ticket summary, document name.",
    )
    url: str | None = Field(
        default=None,
        description="Link back to the original item. Powers the 'View source' button in the UI.",
    )
    author_name: str | None = Field(
        default=None,
        description="Attribution — who wrote this content.",
    )
    timestamp: datetime = Field(
        description="When this content was created in the source system. Must be timezone-aware.",
    )
    score: float = Field(
        ge=0.0,
        le=1.0,
        description="Relevance score for this chunk (0.0 = irrelevant, 1.0 = perfect match).",
    )
    retrieval_method: RetrievalStrategy = Field(
        description="Whether this chunk was found via vector search or graph traversal.",
    )

    @field_validator("content")
    @classmethod
    def content_must_not_be_whitespace_only(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("content cannot be whitespace-only")
        return v

    @field_validator("timestamp", mode="before")
    @classmethod
    def timestamp_must_be_timezone_aware(cls, v: Any) -> Any:
        if isinstance(v, datetime) and v.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware")
        return v


class QueryResponse(BaseModel):
    """
    Response from POST /query — what the API returns after processing a question.

    Contains the LLM-generated answer, the source chunks used to generate it,
    and observability metadata (latency, retrieval count, confidence).
    """

    model_config = ConfigDict(frozen=True)

    query_id: UUID = Field(
        default_factory=uuid4,
        description="Unique ID for this query. Used for logging, tracing, and user feedback.",
    )
    answer: str = Field(
        min_length=1,
        description="The LLM-generated answer to the user's question.",
    )
    sources: list[RetrievedChunk] = Field(
        default_factory=list,
        description="The context chunks used to generate the answer. Shown as citations in the UI.",
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "System confidence in the answer (0.0–1.0). "
            "Derived from source chunk scores. Low confidence = answer may be incomplete."
        ),
    )
    session_id: str = Field(
        description=(
            "Conversation session ID. Always returned — generated if not provided in the request. "
            "Pass this back in the next QueryRequest to continue the conversation."
        ),
    )
    retrieval_count: int = Field(
        ge=0,
        description="Total chunks retrieved before reranking. For observability.",
    )
    processing_time_ms: int = Field(
        ge=0,
        description="End-to-end query processing time in milliseconds.",
    )

    @field_validator("answer")
    @classmethod
    def answer_must_not_be_whitespace_only(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("answer cannot be whitespace-only")
        return v
