# Purpose:      Admin endpoints — system management operations for operators.
#               Provides workspace reset (delete all events + embeddings + graph nodes)
#               and reindex trigger (re-embed all events that lack embeddings).
#               These endpoints are destructive and should be protected by auth in production.
# Called By:    backend/main.py (router)
# Calls:        db/repositories/event_repo.py, db/repositories/vector_repo.py,
#               graph/client.py, memory/vector_indexer.py
# Dependencies: fastapi, sqlalchemy, neo4j
# Test File:    tests/integration/api/test_admin.py

import logging
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models.event import EventModel
from backend.db.models.event_embedding import EventEmbeddingModel
from backend.db.models.entity_registry import EntityRegistryModel
from backend.db.repositories.workspace_repo import workspace_repo
from backend.db.repositories.event_repo import event_repo as ev_repo
from backend.db.session import get_db_session
from backend.graph.client import get_driver

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.post(
    "/reset/{workspace_id}",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Reset all data for a workspace",
    description=(
        "Deletes all events, embeddings, entity registry entries, and graph nodes "
        "for the specified workspace. DESTRUCTIVE — intended for demo resets only."
    ),
)
async def reset_workspace(
    workspace_id: UUID,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Wipes all ingested data for a workspace. Leaves the workspace record itself intact.
    Graph nodes/edges are deleted asynchronously.
    """
    ws = await workspace_repo.get_by_id(session, workspace_id)
    if ws is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace {workspace_id} not found.",
        )

    # Delete embeddings first (FK child of events)
    await session.execute(
        delete(EventEmbeddingModel).where(EventEmbeddingModel.workspace_id == workspace_id)
    )
    # Delete entity registry
    await session.execute(
        delete(EntityRegistryModel).where(EntityRegistryModel.workspace_id == workspace_id)
    )
    # Delete events
    await session.execute(
        delete(EventModel).where(EventModel.workspace_id == workspace_id)
    )
    await session.commit()

    # Neo4j graph reset runs in background to avoid blocking
    background_tasks.add_task(_reset_neo4j_workspace, workspace_id)

    logger.info("Admin: workspace %s reset initiated", workspace_id)
    return {
        "status": "accepted",
        "workspace_id": str(workspace_id),
        "message": "Workspace data deletion initiated. Graph cleanup running in background.",
    }


async def _reset_neo4j_workspace(workspace_id: UUID) -> None:
    """Delete all graph nodes belonging to this workspace."""
    try:
        driver = get_driver()
        async with driver.session() as neo_session:
            await neo_session.run(
                "MATCH (n {workspace_id: $wid}) DETACH DELETE n",
                wid=str(workspace_id),
            )
        logger.info("Admin: Neo4j graph cleared for workspace %s", workspace_id)
    except Exception as exc:
        logger.error("Admin: Neo4j reset failed for workspace %s: %s", workspace_id, exc)


@router.post(
    "/reindex/{workspace_id}",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Re-embed all un-embedded events for a workspace",
    description=(
        "Triggers background re-embedding of all events with embedding_status = PENDING or FAILED. "
        "Useful after model changes or after batch imports without embeddings."
    ),
)
async def reindex_workspace(
    workspace_id: UUID,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Enqueues re-embedding of all events that lack embeddings.
    Returns 404 if workspace does not exist.
    """
    ws = await workspace_repo.get_by_id(session, workspace_id)
    if ws is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace {workspace_id} not found.",
        )

    # Count events needing reindex
    count_result = await session.execute(
        text(
            "SELECT COUNT(*) FROM events WHERE workspace_id = :wid "
            "AND embedding_status IN ('PENDING', 'FAILED')"
        ),
        {"wid": str(workspace_id)},
    )
    pending_count = count_result.scalar() or 0

    background_tasks.add_task(_run_reindex, workspace_id)

    logger.info(
        "Admin: reindex triggered for workspace %s (%d events pending)",
        workspace_id, pending_count,
    )
    return {
        "status": "accepted",
        "workspace_id": str(workspace_id),
        "events_queued": pending_count,
        "message": "Reindex job started in background.",
    }


async def _run_reindex(workspace_id: UUID) -> None:
    """Background reindex: fetch un-embedded events and re-embed them."""
    try:
        from backend.db.session import async_session
        from backend.db.models.event import EventModel
        from backend.memory.vector_indexer import VectorIndexer
        from backend.db.repositories.vector_repo import vector_repo
        from sqlalchemy import select
        from backend.models.enums import EmbeddingStatus

        indexer = VectorIndexer(vector_repo=vector_repo)

        async with async_session() as session:
            stmt = select(EventModel).where(
                EventModel.workspace_id == workspace_id,
                EventModel.embedding_status.in_([EmbeddingStatus.PENDING, EmbeddingStatus.FAILED]),
            )
            result = await session.execute(stmt)
            events = list(result.scalars().all())

            for event in events:
                try:
                    await indexer.index_event(session, event)
                    await session.commit()
                except Exception as e:
                    logger.error("Reindex failed for event %s: %s", event.id, e)
                    await session.rollback()

        logger.info(
            "Admin: reindex complete for workspace %s (%d events processed)",
            workspace_id, len(events),
        )
    except Exception as exc:
        logger.error("Admin: reindex background task failed: %s", exc)
