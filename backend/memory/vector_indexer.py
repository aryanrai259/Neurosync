# Purpose:      Vector indexer — embeds a MemoryObject's content and stores
#               the vector in the event_embeddings table via PgVector.
#               Updates events.embedding_status to EMBEDDED on success, FAILED on error.
#               Embedding generation (Ollama call) runs in a thread pool to avoid
#               blocking the async event loop.
# Called By:    ingestion/worker.py (_process_one_event, Phase 4B step)
# Calls:        memory/embeddings.py (embed_text)
#               db/repositories/vector_repo.py (VectorRepository)
#               core/config.py (embedding_model)
# Dependencies: asyncio, python stdlib (logging)
# Test File:    tests/integration/memory/test_vector_indexer.py

import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import get_settings
from backend.db.repositories.vector_repo import VectorRepository
from backend.memory.embeddings import embed_text
from backend.memory.memory_object import MemoryObject

logger = logging.getLogger(__name__)


class VectorIndexer:
    """
    Embeds a MemoryObject's content and stores it in the event_embeddings table.

    Embedding generation (Ollama HTTP call) is CPU/IO-bound and synchronous.
    It is dispatched to a thread pool via asyncio.to_thread() so it does not
    block the async event loop.

    On success: inserts row into event_embeddings + marks event EMBEDDED.
    On failure: marks event FAILED and re-raises for the worker to log.
    """

    def __init__(self, repo: VectorRepository) -> None:
        self.repo = repo

    async def index(
        self,
        memory_object: MemoryObject,
        session: AsyncSession,
    ) -> None:
        """
        Generate embedding for memory_object.content and persist to DB.

        Args:
            memory_object: Source of content to embed + provenance.
            session:       Active DB session — caller owns the transaction.

        Raises:
            Exception: If embedding generation or DB write fails.
                       Caller (worker) catches this and logs a warning.
        """
        settings = get_settings()

        # Run synchronous embed_text in a thread to avoid blocking the event loop
        try:
            embedding: list[float] = await asyncio.to_thread(
                embed_text, memory_object.content
            )
        except Exception as exc:
            logger.error(
                "vector indexer: embedding failed for event %s: %s",
                memory_object.event_id, exc,
            )
            await self.repo.mark_event_embedding_failed(session, memory_object.event_id)
            raise

        # Persist embedding
        await self.repo.upsert(
            session=session,
            event_id=memory_object.event_id,
            workspace_id=memory_object.workspace_id,
            embedding=embedding,
            model_name=settings.embedding_model,
            chunk_index=0,
        )

        # Update event embedding status
        await self.repo.mark_event_embedded(session, memory_object.event_id)

        logger.debug(
            "vector indexer: embedded event %s (model=%s)",
            memory_object.event_id, settings.embedding_model,
        )
