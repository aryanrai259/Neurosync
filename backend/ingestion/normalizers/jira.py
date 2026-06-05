# Purpose:      Jira ticket normalizer.
#               Converts a RawEvent from a Jira source into a NormalizedEvent.
#               Ticket key becomes the title. Labels, priority, and assignee
#               go into metadata. Authority score is 0.80 (formal work tracking).
# Called By:    ingestion/worker.py (via NORMALIZER_MAP[SourceType.JIRA])
# Calls:        ingestion/normalizers/_parsing.py
#               models/event.py (NormalizedEvent)
#               ingestion/schemas.py (RawEvent)
#               ingestion/constants.py (SOURCE_AUTHORITY_MAP)
# Dependencies: python stdlib (uuid)
# Test File:    tests/unit/ingestion/test_normalizers.py

from uuid import UUID

from backend.ingestion.constants import SOURCE_AUTHORITY_MAP
from backend.ingestion.normalizers._parsing import parse_iso_timestamp
from backend.ingestion.schemas import RawEvent
from backend.models.enums import SourceType
from backend.models.event import NormalizedEvent


class JiraNormalizer:
    """
    Normalizes a raw Jira ticket event into a NormalizedEvent.

    Authority score for Jira is 0.80 — higher than GitHub because Jira tickets
    represent formally assigned, tracked work items with clear ownership.

    The Jira ticket key (e.g., "PROJ-1234") is used as both source_id and
    as part of the title, making it easy to reference in retrieval.
    """

    def normalize(self, raw: RawEvent, workspace_id: UUID) -> NormalizedEvent:
        """
        Convert a Jira RawEvent to a NormalizedEvent.

        Field mapping:
          raw.source_id     → source_id (Jira ticket key, e.g. "PROJ-1234")
          raw.raw_content   → content   (ticket description or comment body)
          raw.raw_author    → author_id (Jira username or account ID)
          raw.raw_timestamp → timestamp (parsed ISO 8601)
          raw.extra         → metadata  (summary, priority, labels, status, authority_score)

        Title format: "PROJ-1234: <summary>" if summary present, else just the key.
        """
        timestamp = parse_iso_timestamp(raw.raw_timestamp)

        summary = raw.extra.get("summary")
        if summary:
            title = f"{raw.source_id}: {summary}"
        else:
            title = raw.source_id

        metadata = {
            **raw.extra,
            "authority_score": SOURCE_AUTHORITY_MAP["jira"],
        }

        return NormalizedEvent(
            source=SourceType.JIRA,
            workspace_id=workspace_id,
            source_id=raw.source_id,
            content=raw.raw_content,
            title=title,
            author_id=raw.raw_author,
            author_name=raw.extra.get("author_name"),
            url=raw.extra.get("url"),
            timestamp=timestamp,
            metadata=metadata,
        )
