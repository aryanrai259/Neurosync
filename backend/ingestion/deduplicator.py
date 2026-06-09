# Purpose:      Deduplication check for the ingestion pipeline.
#               Before persisting an event, the worker checks whether
#               (workspace_id, source, source_id) already exists in the DB.
#               If it does, the event is counted as a duplicate and skipped.
#
#               Note: event_repo.upsert_event already handles the DB-level
#               constraint via ON CONFLICT DO UPDATE. This pre-check exists so
#               the worker can accurately report "skipped" vs "ingested" counts
#               and avoid unnecessary DB writes for exact duplicates.
#
# Called By:    ingestion/worker.py
# Calls:        db/models/event.py (EventModel)
# Dependencies: sqlalchemy (select, AsyncSession)
# Test File:    tests/unit/ingestion/test_deduplicator.py

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models.event import EventModel
from backend.models.enums import SourceType


class Deduplicator:
    """
    Checks whether an event already exists in the events table.

    Design: uses a lightweight SELECT on the indexed unique constraint
    (workspace_id, source, source_id) — the same constraint that
    event_repo.upsert_event enforces at write time.
    """

    async def is_duplicate(
        self,
        session: AsyncSession,
        workspace_id: UUID,
        source: SourceType,
        source_id: str,
    ) -> bool:
        """
        Return True if this (workspace_id, source, source_id) already exists.

        Uses SELECT ... LIMIT 1 on the indexed columns for minimal cost.
        Returning True means the worker will skip this event rather than
        calling upsert_event again.
        """
        stmt = (
            select(EventModel.id)
            .where(EventModel.workspace_id == workspace_id)
            .where(EventModel.source == source)
            .where(EventModel.source_id == source_id)
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.first() is not None
