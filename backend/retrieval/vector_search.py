# Purpose:      Vector search — queries PgVector for events semantically similar
#               to a text query. Returns RetrievedChunks sorted by similarity.
#               Embedding generation is synchronous (via Ollama), dispatched to thread.
# Called By:    retrieval/hybrid.py
# Calls:        memory/embeddings.py (embed_text)
#               db/repositories/vector_repo.py (VectorRepository.search_similar)
#               db/repositories/event_repo.py (EventRepository — hydration)
#               retrieval/schemas.py (RetrievedChunk)
# Dependencies: asyncio, sqlalchemy (AsyncSession), python stdlib (logging)
# Test File:    tests/unit/retrieval/test_hybrid.py

import asyncio
import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models.event import EventModel
from backend.db.repositories.vector_repo import VectorRepository
from backend.memory.embeddings import embed_text
from backend.retrieval.schemas import RetrievedChunk

logger = logging.getLogger(__name__)


async def vector_search(
    session: AsyncSession,
    vector_repo: VectorRepository,
    workspace_id: UUID,
    query: str,
    k: int = 10,
) -> list[RetrievedChunk]:
    """
    Embed the query and return top-K semantically similar events.

    Steps:
      1. Embed the query string via embed_text (in a thread).
      2. Query PgVector for top-K event embeddings by cosine distance.
      3. Hydrate each hit into a RetrievedChunk by fetching the EventModel.

    Returns empty list if Ollama is unavailable or no embeddings exist.

    Args:
        session:     Active DB session.
        vector_repo: VectorRepository instance.
        workspace_id: Scope all results to this workspace.
        query:       User query string.
        k:           Number of results to return.
    """
    if not query or not query.strip():
        return []

    # Step 1: embed the query
    try:
        query_embedding: list[float] = await asyncio.to_thread(embed_text, query)
    except Exception as exc:
        logger.warning("vector_search: embedding failed: %s — returning empty", exc)
        return []

    # Step 2: similarity search
    hits = await vector_repo.search_similar(
        session=session,
        workspace_id=workspace_id,
        query_embedding=query_embedding,
        k=k,
    )

    if not hits:
        return []

    # Step 3: hydrate from events table
    event_ids = [emb.event_id for emb, _ in hits]
    stmt = select(EventModel).where(EventModel.id.in_(event_ids))
    result = await session.execute(stmt)
    events_by_id: dict[UUID, EventModel] = {e.id: e for e in result.scalars().all()}

    chunks: list[RetrievedChunk] = []
    for embedding_model, distance in hits:
        event = events_by_id.get(embedding_model.event_id)
        if event is None:
            continue
        # Convert cosine distance [0,2] to similarity score [0,1]
        similarity = max(0.0, 1.0 - (distance / 2.0))
        chunks.append(RetrievedChunk(
            event_id=event.id,
            content=event.content,
            title=event.title,
            source=event.source,
            timestamp=event.timestamp,
            author_id=event.author_id,
            url=event.url,
            vector_score=round(similarity, 4),
            graph_score=0.0,
            combined_score=round(0.7 * similarity, 4),
        ))

    logger.debug(
        "vector_search: query=%r k=%d hits=%d", query[:40], k, len(chunks)
    )
    return chunks
