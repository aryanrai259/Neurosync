# Purpose:      Vector repository — insert and query event_embeddings table.
#               Provides upsert for inserting embedding rows and
#               cosine similarity search for retrieval (Phase 4D).
#               Also handles updating events.embedding_status after indexing.
# Called By:    memory/vector_indexer.py (writes)
#               retrieval/vector_search.py (reads)
# Calls:        db/models/event_embedding.py (EventEmbeddingModel)
#               db/models/event.py (EventModel — for status update)
# Dependencies: sqlalchemy (AsyncSession), pgvector
# Test File:    tests/integration/memory/test_vector_indexer.py

from uuid import UUID

from sqlalchemy import select, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models.event import EventModel
from backend.db.models.event_embedding import EventEmbeddingModel
from backend.db.repositories.base import BaseRepository
from backend.models.enums import EmbeddingStatus


class VectorRepository(BaseRepository[EventEmbeddingModel]):
    """
    Data access for event_embeddings table.

    Operations:
        upsert:                 Insert or replace an embedding row.
        mark_event_embedded:    Update events.embedding_status → EMBEDDED.
        mark_event_failed:      Update events.embedding_status → FAILED.
        search_similar:         Cosine similarity top-K query (Phase 4D).
    """

    def __init__(self) -> None:
        super().__init__(EventEmbeddingModel)

    async def upsert(
        self,
        session: AsyncSession,
        event_id: UUID,
        workspace_id: UUID,
        embedding: list[float],
        model_name: str,
        chunk_index: int = 0,
    ) -> EventEmbeddingModel:
        """
        Insert an embedding row. On conflict (same event_id + chunk_index),
        update the embedding and model_name.
        Returns the upserted row.
        """
        values = dict(
            event_id=event_id,
            workspace_id=workspace_id,
            chunk_index=chunk_index,
            embedding=embedding,
            model_name=model_name,
        )
        stmt = insert(EventEmbeddingModel).values(**values)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_event_embeddings_event_chunk",
            set_={
                "embedding": stmt.excluded.embedding,
                "model_name": stmt.excluded.model_name,
            },
        ).returning(EventEmbeddingModel)
        result = await session.execute(stmt.execution_options(populate_existing=True))
        await session.flush()
        return result.scalar_one()

    async def mark_event_embedded(
        self,
        session: AsyncSession,
        event_id: UUID,
    ) -> None:
        """Update events.embedding_status to EMBEDDED."""
        stmt = (
            update(EventModel)
            .where(EventModel.id == event_id)
            .values(embedding_status=EmbeddingStatus.EMBEDDED)
        )
        await session.execute(stmt)
        await session.flush()

    async def mark_event_embedding_failed(
        self,
        session: AsyncSession,
        event_id: UUID,
    ) -> None:
        """Update events.embedding_status to FAILED."""
        stmt = (
            update(EventModel)
            .where(EventModel.id == event_id)
            .values(embedding_status=EmbeddingStatus.FAILED)
        )
        await session.execute(stmt)
        await session.flush()

    async def search_similar(
        self,
        session: AsyncSession,
        workspace_id: UUID,
        query_embedding: list[float],
        k: int = 10,
    ) -> list[tuple[EventEmbeddingModel, float]]:
        """
        Return top-K event embeddings by cosine similarity within a workspace.

        Returns a list of (EventEmbeddingModel, distance) tuples sorted by
        ascending cosine distance (smaller = more similar).

        Uses pgvector's <=> operator (cosine distance).
        """
        stmt = (
            select(
                EventEmbeddingModel,
                EventEmbeddingModel.embedding.cosine_distance(query_embedding).label("distance"),
            )
            .where(EventEmbeddingModel.workspace_id == workspace_id)
            .order_by("distance")
            .limit(k)
        )
        result = await session.execute(stmt)
        return [(row.EventEmbeddingModel, row.distance) for row in result]


# Global singleton
vector_repo = VectorRepository()
