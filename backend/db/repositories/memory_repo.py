# Purpose:      Repository for MemoryObjectModel — write-once extraction log.
#               Provides insert and lookup operations for memory_objects.
#               Does NOT update. Replay = delete_by_event_id + insert.
# Called By:    memory/memory_constructor.py
# Calls:        db/models/memory_object.py (MemoryObjectModel)
#               db/repositories/base.py (BaseRepository)
# Dependencies: sqlalchemy (AsyncSession)
# Test File:    tests/integration/memory/test_memory_constructor.py

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models.memory_object import MemoryObjectModel
from backend.db.repositories.base import BaseRepository
from backend.memory.memory_object import MemoryObject


class MemoryObjectRepository(BaseRepository[MemoryObjectModel]):
    """
    Data access for memory_objects table.

    Operations:
        insert:             Write a new MemoryObject extraction result.
        get_by_event_id:    Retrieve an existing extraction result.
        delete_by_event_id: Remove before replay.
    """

    def __init__(self) -> None:
        super().__init__(MemoryObjectModel)

    async def insert(
        self,
        session: AsyncSession,
        memory_object: MemoryObject,
    ) -> MemoryObjectModel:
        """
        Persist a MemoryObject to the memory_objects table.

        Serialises entities and relationships to plain dicts so they
        can be stored as JSONB. Raises IntegrityError if a row for
        this event_id already exists.
        """
        row = MemoryObjectModel(
            event_id=memory_object.event_id,
            workspace_id=memory_object.workspace_id,
            entities=[e.model_dump() for e in memory_object.entities],
            relationships=[r.model_dump() for r in memory_object.relationships],
        )
        session.add(row)
        await session.flush()
        return row

    async def get_by_event_id(
        self,
        session: AsyncSession,
        event_id: UUID,
    ) -> MemoryObjectModel | None:
        """Return the memory object for an event, or None if not found."""
        stmt = select(MemoryObjectModel).where(
            MemoryObjectModel.event_id == event_id
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def delete_by_event_id(
        self,
        session: AsyncSession,
        event_id: UUID,
    ) -> bool:
        """
        Delete the memory object for an event (for replay).
        Returns True if a row was deleted, False if none existed.
        """
        from sqlalchemy import delete as sa_delete
        stmt = sa_delete(MemoryObjectModel).where(
            MemoryObjectModel.event_id == event_id
        )
        result = await session.execute(stmt)
        return result.rowcount > 0


# Global singleton — matches the pattern used by other repos in this project
memory_object_repo = MemoryObjectRepository()
