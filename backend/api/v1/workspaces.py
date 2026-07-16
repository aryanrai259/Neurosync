# Purpose:      Workspace management API endpoints.
#               Provides CRUD operations for workspaces — the top-level tenant boundary.
#               Workspace creation is required before any ingestion or query.
# Called By:    backend/main.py (router)
# Calls:        db/repositories/workspace_repo.py, db/session.py
# Dependencies: fastapi, sqlalchemy
# Test File:    tests/integration/api/test_workspaces.py

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.repositories.workspace_repo import workspace_repo
from backend.db.session import get_db_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/workspaces", tags=["workspaces"])


class CreateWorkspaceRequest(BaseModel):
    name: str


class WorkspaceResponse(BaseModel):
    id: UUID
    name: str

    model_config = {"from_attributes": True}


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=WorkspaceResponse,
    summary="Create a new workspace",
    description="Creates a new workspace — the top-level tenant boundary for all data.",
)
async def create_workspace(
    request: CreateWorkspaceRequest,
    session: AsyncSession = Depends(get_db_session),
) -> WorkspaceResponse:
    """
    Create a workspace. A workspace is required before ingesting events or querying.
    Returns 409 if a workspace with the same name already exists.
    """
    try:
        ws = await workspace_repo.create(session, name=request.name)
        logger.info("Created workspace %s (id=%s)", ws.name, ws.id)
        return WorkspaceResponse(id=ws.id, name=ws.name)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Workspace with this name already exists.",
        )


@router.get(
    "/{workspace_id}",
    response_model=WorkspaceResponse,
    summary="Get workspace by ID",
)
async def get_workspace(
    workspace_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> WorkspaceResponse:
    """
    Returns workspace metadata. Returns 404 if not found.
    """
    ws = await workspace_repo.get_by_id(session, workspace_id)
    if ws is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace {workspace_id} not found.",
        )
    return WorkspaceResponse(id=ws.id, name=ws.name)


@router.get(
    "",
    response_model=list[WorkspaceResponse],
    summary="List all workspaces",
)
async def list_workspaces(
    session: AsyncSession = Depends(get_db_session),
) -> list[WorkspaceResponse]:
    """
    Returns all workspaces. For demo and admin use.
    """
    workspaces = await workspace_repo.list_all(session)
    return [WorkspaceResponse(id=ws.id, name=ws.name) for ws in workspaces]
