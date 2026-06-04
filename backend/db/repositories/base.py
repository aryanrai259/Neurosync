# Purpose:      Base repository pattern.
#               Provides common CRUD operations to avoid duplication in specific repos.
# Called By:    All repositories in backend/db/repositories/
# Dependencies: sqlalchemy

from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """
    Base class for data access repositories.
    Provides common standard methods.
    """

    def __init__(self, model_class: type[ModelType]):
        self.model_class = model_class

    async def get_by_id(self, session: AsyncSession, id: UUID) -> ModelType | None:
        """Fetch a single record by its UUID primary key."""
        stmt = select(self.model_class).where(self.model_class.id == id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def exists(self, session: AsyncSession, id: UUID) -> bool:
        """Check if a record exists by UUID."""
        stmt = select(self.model_class.id).where(self.model_class.id == id)
        result = await session.execute(stmt)
        return result.first() is not None

    async def delete(self, session: AsyncSession, id: UUID) -> bool:
        """
        Delete a record by UUID.
        Returns True if a record was deleted, False if it didn't exist.
        """
        stmt = delete(self.model_class).where(self.model_class.id == id)
        result = await session.execute(stmt)
        return result.rowcount > 0
