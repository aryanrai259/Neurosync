# Purpose:      Workspace repository — CRUD operations for workspace tenant records.
# Called By:    API endpoints (workspaces.py, ingest.py, reasoning.py)
# Dependencies: sqlalchemy
# Test File:    tests/integration/api/test_workspaces.py

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

    async def get_by_name(self, session: AsyncSession, name: str) -> WorkspaceModel | None:
        """Fetch a workspace by its display name (first match)."""
        stmt = select(WorkspaceModel).where(WorkspaceModel.name == name)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self, session: AsyncSession, name: str, slug: str | None = None, config: dict | None = None
    ) -> WorkspaceModel:
        """
        Create a new workspace.
        If slug is not provided, auto-derives it from the name (lowercase, hyphens).
        Caller is responsible for commit/rollback.
        """
        if slug is None:
            slug = name.lower().replace(" ", "-").replace("_", "-")
        workspace = WorkspaceModel(
            name=name,
            slug=slug,
            config=config or {},
        )
        session.add(workspace)
        await session.flush()     # Populate DB-generated UUID
        await session.commit()    # Persist — callers may still commit again (no-op)
        await session.refresh(workspace)
        return workspace

    async def list_all(self, session: AsyncSession) -> list[WorkspaceModel]:
        """Return all workspaces ordered by creation date."""
        stmt = select(WorkspaceModel).order_by(WorkspaceModel.created_at.desc())
        result = await session.execute(stmt)
        return list(result.scalars().all())


# Global instance
workspace_repo = WorkspaceRepository()
