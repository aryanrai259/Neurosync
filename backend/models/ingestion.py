# Purpose:      Ingestion job models — defines what triggers an ingestion run
#               and what comes back when it completes. Used by the ingestion
#               pipeline and the API layer to track data import jobs.
# Called By:    api/ingest.py (receives IngestionRequest, returns IngestionResult)
#               ingestion/scheduler.py (creates IngestionRequest objects)
#               ingestion/slack.py, github.py, etc. (produce IngestionResult)
# Calls:        models/enums.py (SourceType, IngestionStatus)
# Dependencies: pydantic v2, python stdlib (uuid, datetime, typing)
# Test File:    tests/unit/models/test_ingestion.py

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .enums import IngestionStatus, SourceType


class IngestionRequest(BaseModel):
    """
    A request to ingest data from a source into a workspace.

    Created by the scheduler (periodic ingestion) or the API (manual trigger).
    The source_config field holds connection parameters for the specific source
    — API keys, channel IDs, date ranges, etc. Kept as dict[str, Any] to
    accommodate different sources without forcing a rigid schema here.

    source_config should never be logged in plaintext — it may contain tokens.
    """

    model_config = ConfigDict(frozen=True)

    id: UUID = Field(
        default_factory=uuid4,
        description="Unique ID for this ingestion request. Echoed in IngestionResult.",
    )
    workspace_id: UUID = Field(
        description="Which workspace to ingest data into.",
    )
    source: SourceType = Field(
        description="Which source system to pull data from.",
    )
    source_config: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Source-specific connection parameters. "
            "e.g. {'channel_ids': ['C123'], 'since': '2024-01-01'} for Slack. "
            "WARNING: may contain API tokens — never log this field."
        ),
    )
    requested_by: str = Field(
        min_length=1,
        description="ID of the user or system that triggered this ingestion.",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When this ingestion was requested. Always UTC.",
    )

    @field_validator("requested_by")
    @classmethod
    def requested_by_must_not_be_whitespace_only(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("requested_by cannot be whitespace-only")
        return v

    @field_validator("created_at", mode="before")
    @classmethod
    def must_be_timezone_aware(cls, v: Any) -> Any:
        if isinstance(v, datetime) and v.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")
        return v


class IngestionResult(BaseModel):
    """
    The outcome of a completed (or failed) ingestion job.

    Written by the ingestion worker when it finishes processing.
    The API layer reads this to report job status back to the caller.

    On failure: status=FAILED, error_message is set, events_ingested may be
    partial (some events processed before the error).

    On success: status=COMPLETED, error_message is None,
    events_ingested = total events written to storage.
    """

    model_config = ConfigDict(frozen=True)

    request_id: UUID = Field(
        description="ID of the IngestionRequest this result corresponds to.",
    )
    workspace_id: UUID = Field(
        description="Which workspace was ingested into.",
    )
    source: SourceType = Field(
        description="Which source system was ingested.",
    )
    status: IngestionStatus = Field(
        description="Final status of the ingestion job.",
    )
    events_ingested: int = Field(
        default=0,
        ge=0,
        description="Number of NormalizedEvents successfully written to storage.",
    )
    events_failed: int = Field(
        default=0,
        ge=0,
        description="Number of events that could not be processed (parse errors, etc.).",
    )
    error_message: str | None = Field(
        default=None,
        description="Human-readable error description. Set only when status=FAILED.",
    )
    started_at: datetime = Field(
        description="When the ingestion worker began processing. Must be timezone-aware.",
    )
    completed_at: datetime | None = Field(
        default=None,
        description=(
            "When processing finished. None if status is PENDING or PROCESSING. "
            "Always set when status is COMPLETED or FAILED."
        ),
    )
    processing_time_ms: int | None = Field(
        default=None,
        ge=0,
        description="Total processing time in milliseconds. None if not yet complete.",
    )

    @field_validator("started_at", "completed_at", mode="before")
    @classmethod
    def must_be_timezone_aware(cls, v: Any) -> Any:
        if isinstance(v, datetime) and v.tzinfo is None:
            raise ValueError("datetime must be timezone-aware")
        return v
