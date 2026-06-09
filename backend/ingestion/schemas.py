# Purpose:      Ingestion-layer Pydantic schemas.
#               Defines what adapters produce (RawEvent) and what the
#               entity extractor produces (EntityMention). Also defines the
#               HTTP request/response bodies for the ingest API.
# Called By:    ingestion/adapters/synthetic.py (produces RawEvent)
#               ingestion/normalizers/*.py (consumes RawEvent)
#               ingestion/entity_extractor.py (produces EntityMention)
#               api/v1/ingest.py (consumes SyntheticJobRequest, returns JobSubmittedResponse)
# Calls:        models/enums.py (SourceType, EntityType)
# Dependencies: pydantic v2, python stdlib (uuid)

from uuid import UUID

from pydantic import BaseModel, Field

from backend.models.enums import EntityType, IngestionStatus, SourceType


class RawEvent(BaseModel):
    """
    An event as it arrives from an adapter, before normalization.

    Adapters produce this shape — normalizers consume it.
    raw_timestamp is kept as a string so each normalizer can parse the
    source-specific format (ISO 8601 for synthetic, Unix ts for real Slack, etc.)
    """

    source: SourceType
    source_id: str = Field(min_length=1, description="ID in the source system.")
    raw_content: str = Field(min_length=1, description="Unparsed text from the source.")
    raw_author: str = Field(min_length=1, description="Author identifier from source.")
    raw_timestamp: str = Field(
        min_length=1,
        description="ISO 8601 timestamp string. Normalizer parses this.",
    )
    extra: dict = Field(
        default_factory=dict,
        description="Source-specific supplementary fields (channel, PR number, labels…)",
    )


class EntityMention(BaseModel):
    """
    A named entity found inside event text by BasicEntityExtractor.

    These become rows in entity_registry after the worker writes them.
    confidence=1.0 means exact keyword match; lower values for fuzzy matches.
    """

    name: str = Field(min_length=1)
    entity_type: EntityType
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)


class SyntheticJobRequest(BaseModel):
    """
    HTTP request body for POST /api/v1/ingest/synthetic.

    The client sends raw events directly — no external API calls are made.
    This is the synthetic adapter: source data arrives in the request body.
    """

    workspace_id: UUID
    requested_by: str = Field(min_length=1)
    events: list[RawEvent] = Field(min_length=1)


class JobSubmittedResponse(BaseModel):
    """
    HTTP 202 response after a synthetic ingestion job is accepted.

    job_id can be polled via GET /api/v1/ingest/jobs/{job_id} (Phase 6+).
    """

    job_id: UUID
    status: IngestionStatus
    event_count: int


class GithubJobRequest(BaseModel):
    """
    HTTP request body for POST /api/v1/ingest/github.

    Configures the GitHub adapter to fetch recent issues/PRs from a repo.
    """

    workspace_id: UUID
    requested_by: str = Field(min_length=1)
    repo: str = Field(min_length=3, description="Repository in 'owner/repo' format.")

