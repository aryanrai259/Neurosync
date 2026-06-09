# Purpose:      Decision management API endpoints.
#               Provides CRUD operations for organizational decisions.
# Called By:    backend/main.py (router)
# Calls:        db/repositories/decision_repo.py, db/session.py
# Dependencies: fastapi, sqlalchemy
# Test File:    tests/integration/api/test_decisions_api.py

import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.repositories.decision_repo import decision_repo
from backend.db.session import get_db_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/decisions", tags=["decisions"])


class CreateDecisionRequest(BaseModel):
    workspace_id: UUID
    title: str
    description: str | None = None
    status: str = "ACTIVE"
    decision_date: datetime | None = None
    decided_by: str | None = None
    supersedes_id: UUID | None = None
    source_event_id: UUID | None = None
    metadata: dict = {}


class DecisionResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    title: str
    description: str | None
    status: str
    decision_date: datetime | None
    decided_by: str | None
    supersedes_id: UUID | None
    source_event_id: UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=DecisionResponse,
    summary="Create a new decision",
)
async def create_decision(
    request: CreateDecisionRequest,
    session: AsyncSession = Depends(get_db_session),
) -> DecisionResponse:
    """
    Record an organizational decision.
    If supersedes_id is set, the referenced decision is automatically marked SUPERSEDED.
    """
    decision = await decision_repo.create_decision(
        session=session,
        workspace_id=request.workspace_id,
        title=request.title,
        description=request.description,
        status=request.status,
        decision_date=request.decision_date or datetime.now(timezone.utc),
        decided_by=request.decided_by,
        supersedes_id=request.supersedes_id,
        source_event_id=request.source_event_id,
        metadata=request.metadata,
    )
    return DecisionResponse(
        id=decision.id,
        workspace_id=decision.workspace_id,
        title=decision.title,
        description=decision.description,
        status=decision.status,
        decision_date=decision.decision_date,
        decided_by=decision.decided_by,
        supersedes_id=decision.supersedes_id,
        source_event_id=decision.source_event_id,
        created_at=decision.created_at,
    )


@router.get(
    "/{workspace_id}",
    response_model=list[DecisionResponse],
    summary="List decisions for a workspace",
)
async def list_decisions(
    workspace_id: UUID,
    status: str | None = None,
    limit: int = 50,
    session: AsyncSession = Depends(get_db_session),
) -> list[DecisionResponse]:
    """
    List decisions for a workspace.
    Filter by status (ACTIVE, SUPERSEDED, REVERTED, DRAFT) using ?status=ACTIVE.
    """
    decisions = await decision_repo.list_for_workspace(
        session, workspace_id, status=status, limit=limit
    )
    return [
        DecisionResponse(
            id=d.id,
            workspace_id=d.workspace_id,
            title=d.title,
            description=d.description,
            status=d.status,
            decision_date=d.decision_date,
            decided_by=d.decided_by,
            supersedes_id=d.supersedes_id,
            source_event_id=d.source_event_id,
            created_at=d.created_at,
        )
        for d in decisions
    ]


@router.get(
    "/single/{decision_id}",
    response_model=DecisionResponse,
    summary="Get a specific decision by ID",
)
async def get_decision(
    decision_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> DecisionResponse:
    """Fetch a single decision by its UUID. Returns 404 if not found."""
    decision = await decision_repo.get_by_id(session, decision_id)
    if decision is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Decision {decision_id} not found.",
        )
    return DecisionResponse(
        id=decision.id,
        workspace_id=decision.workspace_id,
        title=decision.title,
        description=decision.description,
        status=decision.status,
        decision_date=decision.decision_date,
        decided_by=decision.decided_by,
        supersedes_id=decision.supersedes_id,
        source_event_id=decision.source_event_id,
        created_at=decision.created_at,
    )
