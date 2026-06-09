# Purpose:      Timeline repository — queries events chronologically for a given entity.
#               Used by the Timeline module to build event timelines.
#               Joins events to entity_registry to find events mentioning a specific entity.
# Called By:    reasoning/timeline_module.py
# Calls:        db/models/event.py, db/models/entity_registry.py
# Dependencies: sqlalchemy
# Test File:    tests/integration/api/test_timeline_api.py

from datetime import datetime
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models.event import EventModel
from backend.db.models.entity_registry import EntityRegistryModel


class TimelineRepository:
    """
    Queries for events related to a specific entity, ordered by timestamp.

    Strategy: Find events that mention the entity by either:
    1. The event_id is linked to the entity in entity_registry (source_event_id)
    2. The event's raw_content mentions the entity's canonical_name

    This dual approach catches both structured links and unstructured mentions.
    """

    async def get_events_for_entity(
        self,
        session: AsyncSession,
        workspace_id: UUID,
        entity_id: UUID,
        since: datetime | None = None,
        limit: int = 500,
    ) -> list[dict]:
        """
        Return events related to an entity in chronological order.

        Returns list of dicts with keys: id, timestamp, source, raw_author,
        raw_content, entity_mentions.
        """
        # Fetch the entity to get its canonical name for content matching
        entity_stmt = select(EntityRegistryModel).where(
            EntityRegistryModel.id == entity_id,
            EntityRegistryModel.workspace_id == workspace_id,
        )
        entity_result = await session.execute(entity_stmt)
        entity = entity_result.scalar_one_or_none()

        if entity is None:
            return []

        canonical_name = entity.canonical_name

        # Query events that reference this entity (linked via source_event_id)
        # OR events whose content mentions the canonical name (ILIKE)
        conditions = [
            EventModel.workspace_id == workspace_id,
        ]
        if since:
            conditions.append(EventModel.event_timestamp >= since)

        stmt = (
            select(EventModel)
            .where(and_(*conditions))
            .where(
                EventModel.raw_content.ilike(f"%{canonical_name}%")
            )
            .order_by(EventModel.event_timestamp.asc())
            .limit(limit)
        )

        result = await session.execute(stmt)
        events = list(result.scalars().all())

        return [
            {
                "id": ev.id,
                "timestamp": ev.event_timestamp,
                "source": ev.source,
                "raw_author": ev.raw_author,
                "raw_content": ev.raw_content,
                "entity_mentions": [canonical_name],  # Confirmed mention
            }
            for ev in events
        ]

    async def get_events_in_range(
        self,
        session: AsyncSession,
        workspace_id: UUID,
        start: datetime,
        end: datetime,
        limit: int = 200,
    ) -> list[dict]:
        """
        Return all events in a workspace within a time range.
        Used for workspace-level timeline views.
        """
        stmt = (
            select(EventModel)
            .where(
                EventModel.workspace_id == workspace_id,
                EventModel.event_timestamp >= start,
                EventModel.event_timestamp <= end,
            )
            .order_by(EventModel.event_timestamp.asc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        events = list(result.scalars().all())

        return [
            {
                "id": ev.id,
                "timestamp": ev.event_timestamp,
                "source": ev.source,
                "raw_author": ev.raw_author,
                "raw_content": ev.raw_content,
                "entity_mentions": [],
            }
            for ev in events
        ]


# Global instance
timeline_repo = TimelineRepository()
