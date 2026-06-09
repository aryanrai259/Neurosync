# Purpose:      Slack message normalizer.
#               Converts a RawEvent from a Slack source into a NormalizedEvent.
#               Strips mention markup, parses timestamps, and maps Slack-specific
#               fields (channel, thread_ts, reactions) into the metadata dict.
# Called By:    ingestion/worker.py (via NORMALIZER_MAP[SourceType.SLACK])
# Calls:        ingestion/normalizers/_parsing.py
#               models/event.py (NormalizedEvent)
#               ingestion/schemas.py (RawEvent)
#               ingestion/constants.py (SOURCE_AUTHORITY_MAP)
# Dependencies: python stdlib (uuid), pydantic
# Test File:    tests/unit/ingestion/test_normalizers.py

from uuid import UUID

from backend.ingestion.constants import SOURCE_AUTHORITY_MAP
from backend.ingestion.normalizers._parsing import parse_iso_timestamp, strip_slack_mentions
from backend.ingestion.schemas import RawEvent
from backend.models.enums import SourceType
from backend.models.event import NormalizedEvent


class SlackNormalizer:
    """
    Normalizes a raw Slack message event into a NormalizedEvent.

    Authority score for Slack is 0.60 — the weakest source. Slack messages
    are the noisiest signal: informal, unverified, and often conversational.
    The score is stored in metadata so retrieval can factor it in.
    """

    def normalize(self, raw: RawEvent, workspace_id: UUID) -> NormalizedEvent:
        """
        Convert a Slack RawEvent to a NormalizedEvent.

        Field mapping:
          raw.source_id     → source_id (Slack message timestamp, e.g. "1716000000.000001")
          raw.raw_content   → content   (mention markup stripped)
          raw.raw_author    → author_id (Slack user ID)
          raw.raw_timestamp → timestamp (parsed ISO 8601 → timezone-aware datetime)
          raw.extra         → metadata  (channel, thread_ts, reactions, authority_score)
        """
        content = strip_slack_mentions(raw.raw_content)
        timestamp = parse_iso_timestamp(raw.raw_timestamp)

        metadata = {
            **raw.extra,
            "authority_score": SOURCE_AUTHORITY_MAP["slack"],
        }

        return NormalizedEvent(
            source=SourceType.SLACK,
            workspace_id=workspace_id,
            source_id=raw.source_id,
            content=content,
            title=None,  # Slack messages have no title
            author_id=raw.raw_author,
            author_name=raw.extra.get("author_name"),
            url=raw.extra.get("url"),
            timestamp=timestamp,
            metadata=metadata,
        )
