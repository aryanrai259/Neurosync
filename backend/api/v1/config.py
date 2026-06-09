# Purpose:      REST API endpoints for the Configuration Registry.
# Called By:    FastAPI router.
# Dependencies: fastapi, config_repo, service.py

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config.service import config_graph_syncer
from backend.db.repositories.config_repo import config_repo
from backend.db.session import get_db_session

router = APIRouter(prefix="/api/v1/config", tags=["config"])


@router.post("/sync/{workspace_id}")
async def sync_config_to_neo4j(workspace_id: UUID, session: AsyncSession = Depends(get_db_session)):
    """Manually trigger a sync of the PostgreSQL config to Neo4j."""
    await config_graph_syncer.sync_workspace(session, workspace_id)
    return {"status": "success", "message": "Graph sync complete"}


@router.get("/teams/{workspace_id}")
async def get_teams(workspace_id: UUID, session: AsyncSession = Depends(get_db_session)):
    return await config_repo.get_teams(session, workspace_id)


@router.post("/teams/{workspace_id}")
async def create_team(
    workspace_id: UUID, name: str, description: str | None = None, session: AsyncSession = Depends(get_db_session)
):
    team = await config_repo.upsert_team(session, workspace_id, name, description)
    await session.commit()
    return team


@router.get("/services/{workspace_id}")
async def get_services(workspace_id: UUID, session: AsyncSession = Depends(get_db_session)):
    return await config_repo.get_services(session, workspace_id)


@router.post("/services/{workspace_id}")
async def create_service(workspace_id: UUID, name: str, session: AsyncSession = Depends(get_db_session)):
    service = await config_repo.upsert_service(session, workspace_id, name)
    await session.commit()
    return service


@router.post("/repositories/{workspace_id}")
async def create_repository(
    workspace_id: UUID, repo_url: str, service_id: UUID, session: AsyncSession = Depends(get_db_session)
):
    repo = await config_repo.upsert_repository(session, workspace_id, repo_url, service_id)
    await session.commit()
    return repo
