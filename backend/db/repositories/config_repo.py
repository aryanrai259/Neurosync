# Purpose:      Database repository for Configuration Registry operations.
#               Provides CRUD operations and version tracking for Phase 5 config.
# Called By:    config/service.py, api/v1/config.py
# Dependencies: sqlalchemy

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models.config import (
    ConfigDependencyModel,
    ConfigOwnershipModel,
    ConfigRegistryVersionModel,
    ConfigRepositoryModel,
    ConfigServiceModel,
    ConfigTeamModel,
)


class ConfigRepository:
    """Repository for managing Workspace Configuration Registry."""

    async def bump_version(self, session: AsyncSession, workspace_id: UUID) -> int:
        """
        Increments and returns the new config_registry_version for a workspace.
        Creates version=1 if none exists.
        """
        stmt = (
            insert(ConfigRegistryVersionModel)
            .values(workspace_id=workspace_id, version=1)
            .on_conflict_do_update(
                index_elements=["workspace_id"],
                set_={"version": ConfigRegistryVersionModel.version + 1},
            )
            .returning(ConfigRegistryVersionModel.version)
        )
        result = await session.execute(stmt)
        return result.scalar_one()

    async def get_version(self, session: AsyncSession, workspace_id: UUID) -> int:
        """Get the current config registry version, returns 0 if none exists."""
        stmt = select(ConfigRegistryVersionModel.version).where(
            ConfigRegistryVersionModel.workspace_id == workspace_id
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none() or 0

    async def get_known_entities(self, session: AsyncSession, workspace_id: UUID) -> set[str]:
        """Returns a flat set of all known team names, service names, and repository urls for intent routing."""
        entities = set()
        
        # Teams
        stmt = select(ConfigTeamModel.name).where(ConfigTeamModel.workspace_id == workspace_id)
        for row in (await session.execute(stmt)).scalars():
            entities.add(row)
            
        # Services
        stmt = select(ConfigServiceModel.name).where(ConfigServiceModel.workspace_id == workspace_id)
        for row in (await session.execute(stmt)).scalars():
            entities.add(row)
            
        # Repos
        stmt = select(ConfigRepositoryModel.repo_url).where(ConfigRepositoryModel.workspace_id == workspace_id)
        for row in (await session.execute(stmt)).scalars():
            entities.add(row)
            
        return entities

    # --- Teams ---

    async def get_teams(self, session: AsyncSession, workspace_id: UUID) -> Sequence[ConfigTeamModel]:
        stmt = select(ConfigTeamModel).where(ConfigTeamModel.workspace_id == workspace_id)
        result = await session.execute(stmt)
        return result.scalars().all()

    async def upsert_team(
        self, session: AsyncSession, workspace_id: UUID, name: str, description: str | None = None
    ) -> ConfigTeamModel:
        stmt = (
            insert(ConfigTeamModel)
            .values(workspace_id=workspace_id, name=name, description=description)
            .on_conflict_do_update(
                index_elements=["workspace_id", "name"],
                set_={"description": description},
            )
            .returning(ConfigTeamModel)
        )
        result = await session.execute(stmt)
        await self.bump_version(session, workspace_id)
        return result.scalar_one()

    async def delete_team(self, session: AsyncSession, workspace_id: UUID, team_id: UUID) -> bool:
        stmt = delete(ConfigTeamModel).where(
            ConfigTeamModel.workspace_id == workspace_id, ConfigTeamModel.id == team_id
        )
        result = await session.execute(stmt)
        if result.rowcount > 0:
            await self.bump_version(session, workspace_id)
            return True
        return False

    # --- Services ---

    async def get_services(self, session: AsyncSession, workspace_id: UUID) -> Sequence[ConfigServiceModel]:
        stmt = select(ConfigServiceModel).where(ConfigServiceModel.workspace_id == workspace_id)
        result = await session.execute(stmt)
        return result.scalars().all()

    async def upsert_service(self, session: AsyncSession, workspace_id: UUID, name: str) -> ConfigServiceModel:
        stmt = (
            insert(ConfigServiceModel)
            .values(workspace_id=workspace_id, name=name)
            .on_conflict_do_nothing(index_elements=["workspace_id", "name"])
            .returning(ConfigServiceModel)
        )
        result = await session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            # It already existed, let's fetch it
            fetch_stmt = select(ConfigServiceModel).where(
                ConfigServiceModel.workspace_id == workspace_id, ConfigServiceModel.name == name
            )
            model = (await session.execute(fetch_stmt)).scalar_one()
        else:
            await self.bump_version(session, workspace_id)
        return model

    async def delete_service(self, session: AsyncSession, workspace_id: UUID, service_id: UUID) -> bool:
        stmt = delete(ConfigServiceModel).where(
            ConfigServiceModel.workspace_id == workspace_id, ConfigServiceModel.id == service_id
        )
        result = await session.execute(stmt)
        if result.rowcount > 0:
            await self.bump_version(session, workspace_id)
            return True
        return False

    # --- Repositories ---

    async def get_repositories(self, session: AsyncSession, workspace_id: UUID) -> Sequence[ConfigRepositoryModel]:
        stmt = select(ConfigRepositoryModel).where(ConfigRepositoryModel.workspace_id == workspace_id)
        result = await session.execute(stmt)
        return result.scalars().all()

    async def upsert_repository(
        self, session: AsyncSession, workspace_id: UUID, repo_url: str, service_id: UUID
    ) -> ConfigRepositoryModel:
        stmt = (
            insert(ConfigRepositoryModel)
            .values(workspace_id=workspace_id, repo_url=repo_url, service_id=service_id)
            .on_conflict_do_update(
                index_elements=["workspace_id", "repo_url"],
                set_={"service_id": service_id},
            )
            .returning(ConfigRepositoryModel)
        )
        result = await session.execute(stmt)
        await self.bump_version(session, workspace_id)
        return result.scalar_one()

    # --- Ownership and Dependencies (Bulk Overwrite Strategy) ---

    async def get_ownership(self, session: AsyncSession, workspace_id: UUID) -> Sequence[ConfigOwnershipModel]:
        stmt = select(ConfigOwnershipModel).where(ConfigOwnershipModel.workspace_id == workspace_id)
        result = await session.execute(stmt)
        return result.scalars().all()

    async def overwrite_ownership(self, session: AsyncSession, workspace_id: UUID, mappings: list[dict]):
        """Mappings is a list of {'team_id': UUID, 'service_id': UUID}"""
        await session.execute(delete(ConfigOwnershipModel).where(ConfigOwnershipModel.workspace_id == workspace_id))
        if mappings:
            values = [
                {
                    "team_id": m["team_id"],
                    "service_id": m["service_id"],
                    "workspace_id": workspace_id,
                }
                for m in mappings
            ]
            await session.execute(insert(ConfigOwnershipModel).values(values))
        await self.bump_version(session, workspace_id)

    async def get_dependencies(self, session: AsyncSession, workspace_id: UUID) -> Sequence[ConfigDependencyModel]:
        stmt = select(ConfigDependencyModel).where(ConfigDependencyModel.workspace_id == workspace_id)
        result = await session.execute(stmt)
        return result.scalars().all()

    async def overwrite_dependencies(self, session: AsyncSession, workspace_id: UUID, mappings: list[dict]):
        """Mappings is a list of {'service_id': UUID, 'depends_on_service_id': UUID}"""
        
        # Cycle Detection via Topological Sort (DFS)
        if mappings:
            from collections import defaultdict
            graph = defaultdict(list)
            for m in mappings:
                graph[m["service_id"]].append(m["depends_on_service_id"])
            
            visited = set()
            rec_stack = set()
            
            def is_cyclic(node):
                visited.add(node)
                rec_stack.add(node)
                
                for neighbor in graph[node]:
                    if neighbor not in visited:
                        if is_cyclic(neighbor):
                            return True
                    elif neighbor in rec_stack:
                        return True
                
                rec_stack.remove(node)
                return False
                
            for node in graph.keys():
                if node not in visited:
                    if is_cyclic(node):
                        raise ValueError("Dependency cycle detected! Cannot persist cyclic dependencies.")

        await session.execute(
            delete(ConfigDependencyModel).where(ConfigDependencyModel.workspace_id == workspace_id)
        )
        if mappings:
            values = [
                {
                    "service_id": m["service_id"],
                    "depends_on_service_id": m["depends_on_service_id"],
                    "workspace_id": workspace_id,
                }
                for m in mappings
            ]
            await session.execute(insert(ConfigDependencyModel).values(values))
        await self.bump_version(session, workspace_id)


config_repo = ConfigRepository()
