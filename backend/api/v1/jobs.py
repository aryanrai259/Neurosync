# Purpose:      Job status polling endpoint.
#               Clients submit ingestion jobs and receive a job_id immediately (202).
#               This endpoint allows them to poll the status of that job.
# Called By:    backend/main.py (router)
# Calls:        db/repositories/ingestion_repo.py, db/session.py
# Dependencies: fastapi, sqlalchemy
# Test File:    tests/integration/api/test_jobs.py

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.repositories.ingestion_repo import ingestion_repo
from backend.db.session import get_db_session
from backend.models.enums import IngestionStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


class JobStatusResponse(BaseModel):
    job_id: UUID
    status: IngestionStatus
    workspace_id: UUID
    source: str
    event_count: int | None = None

    model_config = {"from_attributes": True}


@router.get(
    "/{job_id}",
    response_model=JobStatusResponse,
    summary="Poll ingestion job status",
    description=(
        "Returns the current status of an ingestion job. "
        "Status transitions: PENDING → PROCESSING → COMPLETED | FAILED."
    ),
)
async def get_job_status(
    job_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> JobStatusResponse:
    """
    Poll for the completion of an ingestion job submitted via /api/v1/ingest/*.
    Returns 404 if the job ID does not exist.
    """
    job = await ingestion_repo.get_job(session, job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found.",
        )

    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        workspace_id=job.workspace_id,
        source=job.source.value if hasattr(job.source, "value") else str(job.source),
        event_count=job.event_count if hasattr(job, "event_count") else None,
    )
