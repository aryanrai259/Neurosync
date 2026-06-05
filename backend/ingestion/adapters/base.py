# Purpose:      Base adapter interface for the ingestion pipeline.
#               All source-specific adapters must implement this interface.
# Called By:    ingestion/worker.py
# Calls:        nothing
# Dependencies: abc, ingestion/schemas.py (RawEvent)

from abc import ABC, abstractmethod

from backend.ingestion.schemas import RawEvent


class BaseAdapter(ABC):
    """
    Interface for all source-specific ingestion adapters.

    Adapters are responsible for fetching data from their source system
    and converting it into a list of generic RawEvent objects. They must
    NOT perform normalization or entity extraction.
    """

    @abstractmethod
    async def fetch_events(self) -> list[RawEvent]:
        """
        Fetch events from the configured source.

        Returns:
            A list of RawEvent objects.

        Raises:
            Any source-specific exception (e.g., HTTP error) if the fetch fails.
            The worker will catch this and mark the ingestion job as FAILED.
        """
        pass
