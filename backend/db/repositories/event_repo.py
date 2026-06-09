# Purpose:      Event repository.
# Called By:    Ingestion workers, retrieval layer.
# Dependencies: sqlalchemy

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models.event import EventModel
from backend.db.repositories.base import BaseRepository
from backend.models.enums import EmbeddingStatus, SourceType


class EventRepository(BaseRepository[EventModel]):
    """Repository for EventModel."""

    def __init__(self):
        super().__init__(EventModel)

    async def upsert_event(
        self,
        session: AsyncSession,
        workspace_id: UUID,
        source: SourceType,
        source_id: str,
        content: str,
        author_id: str,
        timestamp: datetime,
        title: str | None = None,
        author_name: str | None = None,
        url: str | None = None,
        metadata_json: dict | None = None,
    ) -> EventModel:
        """
        Insert a new event, or update it if (workspace_id, source, source_id) exists.
        Returns the upserted event.
        """
        values = dict(
            workspace_id=workspace_id,
            source=source,
            source_id=source_id,
            content=content,
            author_id=author_id,
            timestamp=timestamp,
            title=title,
            author_name=author_name,
            url=url,
            metadata_json=metadata_json or {},
        )

        stmt = insert(EventModel).values(**values)

        # On conflict, update the content and metadata (and optionally reset embedding status)
        update_dict = {
            "content": stmt.excluded.content,
            "title": stmt.excluded.title,
            "metadata_json": stmt.excluded.metadata_json,
            # If the content changes, we probably need to re-embed it
            "embedding_status": EmbeddingStatus.PENDING,
            "updated_at": datetime.utcnow(),
        }

        stmt = stmt.on_conflict_do_update(
            index_elements=["workspace_id", "source", "source_id"],
            set_=update_dict,
        ).returning(EventModel)

        result = await session.execute(stmt.execution_options(populate_existing=True))
        await session.commit()
        return result.scalar_one()

    async def get_unembedded_events(self, session: AsyncSession, limit: int = 100) -> Sequence[EventModel]:
        """Fetch events that need vectorization."""
        stmt = (
            select(EventModel)
            .where(EventModel.embedding_status == EmbeddingStatus.PENDING)
            .order_by(EventModel.created_at.asc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        return result.scalars().all()

# Global instance
event_repo = EventRepository()
