# Purpose:      Workspace repository.
# Called By:    API endpoints dealing with workspaces.
# Dependencies: sqlalchemy

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models.workspace import WorkspaceModel
from backend.db.repositories.base import BaseRepository


class WorkspaceRepository(BaseRepository[WorkspaceModel]):
    """Repository for WorkspaceModel."""

    def __init__(self):
        super().__init__(WorkspaceModel)

    async def get_by_slug(self, session: AsyncSession, slug: str) -> WorkspaceModel | None:
        """Fetch a workspace by its unique slug."""
        stmt = select(WorkspaceModel).where(WorkspaceModel.slug == slug)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self, session: AsyncSession, name: str, slug: str, config: dict | None = None
    ) -> WorkspaceModel:
        """Create a new workspace."""
        workspace = WorkspaceModel(
            name=name,
            slug=slug,
            config=config or {}
        )
        session.add(workspace)
        await session.commit()
        await session.refresh(workspace)
        return workspace

# Global instance
workspace_repo = WorkspaceRepository()
