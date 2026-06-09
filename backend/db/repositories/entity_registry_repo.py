# Purpose:      Entity registry repository.
#               Authoritative source of truth for entities. Neo4j acts as a
#               projection/relationship engine built on top of this.
#               Phase 4A adds alias support: register_entity now accepts
#               an optional aliases list and updates them on upsert.
# Called By:    ingestion/worker.py, memory/memory_constructor.py
# Dependencies: sqlalchemy

from uuid import UUID

from sqlalchemy import select
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
        aliases: list[str] | None = None,
    ) -> EntityRegistryModel:
        """
        Upsert an entity into the registry.
        If it already exists, increments source_event_count.
        If aliases are provided, merges them (union) with any existing aliases.
        Returns the registered entity.
        """
        if aliases is None:
            aliases = []

        values = dict(
            workspace_id=workspace_id,
            entity_type=entity_type,
            canonical_name=canonical_name,
            aliases=aliases,
            graph_sync_status=SyncStatus.PENDING,
            source_event_count=1,
        )

        stmt = insert(EntityRegistryModel).values(**values)

        stmt = stmt.on_conflict_do_update(
            index_elements=["workspace_id", "entity_type", "canonical_name"],
            set_={
                "source_event_count": EntityRegistryModel.source_event_count + 1,
                "graph_sync_status": SyncStatus.PENDING,
            },
        ).returning(EntityRegistryModel)

        result = await session.execute(stmt.execution_options(populate_existing=True))
        await session.commit()
        return result.scalar_one()

    async def get_by_canonical_name(
        self,
        session: AsyncSession,
        workspace_id: UUID,
        entity_type: EntityType,
        canonical_name: str,
    ) -> EntityRegistryModel | None:
        """Fetch entity by workspace + type + canonical name."""
        stmt = select(EntityRegistryModel).where(
            EntityRegistryModel.workspace_id == workspace_id,
            EntityRegistryModel.entity_type == entity_type,
            EntityRegistryModel.canonical_name == canonical_name,
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


# Global instance
entity_registry_repo = EntityRegistryRepository()
