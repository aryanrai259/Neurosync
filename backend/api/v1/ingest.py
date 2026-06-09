# Purpose:      Ingestion API router — /api/v1/ingest/*
#               Accepts ingestion job submissions and dispatches them to the
#               IngestionWorker via FastAPI BackgroundTasks.
#
#               Phase 3A: POST /api/v1/ingest/synthetic only.
#               Phase 3B: POST /api/v1/ingest/github will be added here.
#
#               The endpoint validates the request and workspace, creates the
#               job record synchronously (so the caller has a job_id to track),
#               then returns 202 immediately. The worker runs asynchronously
#               after the response is sent.
#
# Called By:    backend/main.py (router registration)
# Calls:        ingestion/worker.py (IngestionWorker.run_job via BackgroundTasks)
#               ingestion/schemas.py (SyntheticJobRequest, JobSubmittedResponse)
#               db/repositories/ingestion_repo.py
#               db/repositories/workspace_repo.py
#               db/session.py (get_db_session)
# Dependencies: fastapi, sqlalchemy (AsyncSession)
# Test File:    tests/integration/ingestion/test_ingest_api.py

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.middleware.auth import require_api_key
from backend.db.models.api_key import ApiKeyModel
from backend.db.repositories.entity_registry_repo import entity_registry_repo
from backend.db.repositories.event_repo import event_repo
from backend.db.repositories.ingestion_repo import ingestion_repo
from backend.db.repositories.workspace_repo import workspace_repo
from backend.db.session import get_db_session
from backend.ingestion.adapters.base import BaseAdapter
from backend.ingestion.adapters.github import GitHubAdapter
from backend.ingestion.adapters.synthetic import SyntheticAdapter
from backend.ingestion.deduplicator import Deduplicator
from backend.ingestion.entity_extractor import BasicEntityExtractor
from backend.ingestion.schemas import GithubJobRequest, JobSubmittedResponse, SyntheticJobRequest
from backend.ingestion.worker import IngestionWorker
from backend.models.enums import IngestionStatus, SourceType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingest", tags=["ingestion"])


def _build_worker(adapter: BaseAdapter) -> IngestionWorker:
    """
    Construct the IngestionWorker with its dependencies.

    Called once per request. All dependencies are stateless singletons
    except the session factory, which defaults to the global async_session.
    """
    return IngestionWorker(
        adapter=adapter,
        deduplicator=Deduplicator(),
        extractor=BasicEntityExtractor(),
        event_repo=event_repo,
        ingestion_repo=ingestion_repo,
        entity_registry_repo=entity_registry_repo,
    )


@router.post(
    "/synthetic",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=JobSubmittedResponse,
    summary="Submit a synthetic ingestion job",
    description=(
        "Accepts a list of pre-formed raw events and queues them for ingestion. "
        "Returns 202 immediately with a job_id. "
        "The pipeline runs asynchronously: normalize → deduplicate → persist → extract entities."
    ),
)
async def submit_synthetic_job(
    request: SyntheticJobRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db_session),
    _api_key: ApiKeyModel = Depends(require_api_key),
) -> JobSubmittedResponse:
    """
    Submit raw events for synthetic ingestion.

    Flow:
      1. Validate workspace exists.
      2. Create ingestion job record (status=PENDING).
      3. Return 202 with job_id.
      4. Worker runs in background: PENDING → PROCESSING → COMPLETED/FAILED.
    """
    # Validate workspace exists
    ws = await workspace_repo.get_by_id(session, request.workspace_id)
    if ws is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace {request.workspace_id} not found.",
        )

    # Create the job record so the caller has a job_id immediately
    job = await ingestion_repo.create_job(
        session=session,
        workspace_id=request.workspace_id,
        source=SourceType.SLACK,  # synthetic jobs may mix sources; use SLACK as placeholder
        source_config={"mode": "synthetic", "event_count": len(request.events)},
        requested_by=request.requested_by,
    )

    logger.info(
        "ingestion job %s created for workspace %s (%d events)",
        job.id, request.workspace_id, len(request.events),
    )

    # Dispatch to background worker — request returns 202 now
    worker = _build_worker(adapter=SyntheticAdapter(events=request.events))
    background_tasks.add_task(worker.run_job, job.id)

    return JobSubmittedResponse(
        job_id=job.id,
        status=IngestionStatus.PENDING,
        event_count=len(request.events),
    )


@router.post(
    "/github",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=JobSubmittedResponse,
    summary="Submit a GitHub ingestion job",
    description="Fetches recent issues and PRs from a specified GitHub repository.",
)
async def submit_github_job(
    request: GithubJobRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db_session),
    _api_key: ApiKeyModel = Depends(require_api_key),
) -> JobSubmittedResponse:
    """
    Submit a GitHub repository for ingestion.
    """
    ws = await workspace_repo.get_by_id(session, request.workspace_id)
    if ws is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace {request.workspace_id} not found.",
        )

    job = await ingestion_repo.create_job(
        session=session,
        workspace_id=request.workspace_id,
        source=SourceType.GITHUB,
        source_config={"mode": "github_live", "repo": request.repo},
        requested_by=request.requested_by,
    )

    logger.info(
        "ingestion job %s created for workspace %s (GitHub %s)",
        job.id, request.workspace_id, request.repo,
    )

    worker = _build_worker(adapter=GitHubAdapter(repo=request.repo, limit=10))
    background_tasks.add_task(worker.run_job, job.id)

    return JobSubmittedResponse(
        job_id=job.id,
        status=IngestionStatus.PENDING,
        event_count=0,  # Unknown at submission time for live adapters
    )
