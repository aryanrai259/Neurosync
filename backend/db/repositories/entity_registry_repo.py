# Purpose:      Entity registry repository.
# Called By:    Graph sync workers, entity extraction layer.
# Dependencies: sqlalchemy

from uuid import UUID

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models.entity_registry import EntityRegistryModel
from backend.db.repositories.base import BaseRepository
from backend.models.enums import EntityType, SyncStatus


class EntityRegistryRepository(BaseRepository[EntityRegistryModel]):
    """Repository for EntityRegistryModel."""

    def __init__(self):
        super().__init__(EntityRegistryModel)

    async def register_entity(
        self,
        session: AsyncSession,
        workspace_id: UUID,
        entity_type: EntityType,
        canonical_name: str,
    ) -> EntityRegistryModel:
        """
        Upsert an entity into the registry.
        If it already exists, increments its source_event_count.
        Returns the registered entity.
        """
        values = dict(
            workspace_id=workspace_id,
            entity_type=entity_type,
            canonical_name=canonical_name,
            graph_sync_status=SyncStatus.PENDING,
            source_event_count=1,
        )

        stmt = insert(EntityRegistryModel).values(**values)

        stmt = stmt.on_conflict_do_update(
            index_elements=["workspace_id", "entity_type", "canonical_name"],
            set_={
                "source_event_count": EntityRegistryModel.source_event_count + 1,
                # If we've seen it again, maybe it needs graph sync
                "graph_sync_status": SyncStatus.PENDING,
            },
        ).returning(EntityRegistryModel)

        result = await session.execute(stmt.execution_options(populate_existing=True))
        await session.commit()
        return result.scalar_one()

# Global instance
entity_registry_repo = EntityRegistryRepository()
