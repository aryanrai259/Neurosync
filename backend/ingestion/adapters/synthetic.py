# Purpose:      Synthetic data adapter.
#               In Phase 3A there are no live external sources. This adapter
#               accepts pre-constructed RawEvent objects directly from the
#               API request body and returns them unchanged.
#
#               This is the entry point for all Phase 3A testing. The adapter
#               pattern here means Phase 3B can add a GitHubAdapter with the
#               same interface without touching the worker or normalizers.
#
# Called By:    ingestion/worker.py
# Calls:        nothing (pure pass-through)
# Dependencies: ingestion/schemas.py (RawEvent)
# Test File:    tests/unit/ingestion/test_adapters.py

from backend.ingestion.adapters.base import BaseAdapter
from backend.ingestion.schemas import RawEvent


class SyntheticAdapter(BaseAdapter):
    """
    A pass-through adapter that returns the raw events it was given.

    In production adapters (GitHub, Slack), this class would make HTTP
    calls to external APIs and return fetched events. For synthetic data,
    the events arrive in the request body and just need to be validated
    before passing to the normalizer.

    Usage:
        adapter = SyntheticAdapter(events_from_request)
        raw_events = await adapter.fetch_events()
    """

    def __init__(self, events: list[RawEvent]):
        self.events = events

    async def fetch_events(self) -> list[RawEvent]:
        """
        Return the provided events as-is.

        Validates that each event is a proper RawEvent by construction
        (Pydantic validation already ran at the API boundary). No external
        I/O is performed — synthetic events arrive pre-formed.
        """
        return list(self.events)
