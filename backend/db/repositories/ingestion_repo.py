# Purpose:      Ingestion repository.
# Called By:    Ingestion API, workers.
# Dependencies: sqlalchemy

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models.ingestion import IngestionJobModel
from backend.db.repositories.base import BaseRepository
from backend.models.enums import IngestionStatus, SourceType


class IngestionRepository(BaseRepository[IngestionJobModel]):
    """Repository for IngestionJobModel."""

    def __init__(self):
        super().__init__(IngestionJobModel)

    async def create_job(
        self,
        session: AsyncSession,
        workspace_id: UUID,
        source: SourceType,
        source_config: dict,
        requested_by: str,
    ) -> IngestionJobModel:
        """Create a new pending ingestion job."""
        job = IngestionJobModel(
            workspace_id=workspace_id,
            source=source,
            source_config=source_config,
            requested_by=requested_by,
            status=IngestionStatus.PENDING,
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)
        return job

    async def mark_processing(self, session: AsyncSession, job_id: UUID) -> bool:
        """Transition job from PENDING to PROCESSING."""
        stmt = (
            update(IngestionJobModel)
            .where(IngestionJobModel.id == job_id)
            .where(IngestionJobModel.status == IngestionStatus.PENDING)
            .values(
                status=IngestionStatus.PROCESSING,
                started_at=datetime.now(timezone.utc),
            )
        )
        result = await session.execute(stmt)
        await session.commit()
        return result.rowcount > 0

    async def mark_completed(
        self,
        session: AsyncSession,
        job_id: UUID,
        events_ingested: int,
        events_failed: int,
        processing_time_ms: int,
    ) -> bool:
        """Transition job to COMPLETED with stats."""
        stmt = (
            update(IngestionJobModel)
            .where(IngestionJobModel.id == job_id)
            .values(
                status=IngestionStatus.COMPLETED,
                completed_at=datetime.now(timezone.utc),
                events_ingested=events_ingested,
                events_failed=events_failed,
                processing_time_ms=processing_time_ms,
            )
        )
        result = await session.execute(stmt)
        await session.commit()
        return result.rowcount > 0

    async def mark_failed(
        self,
        session: AsyncSession,
        job_id: UUID,
        error_message: str,
    ) -> bool:
        """Transition job to FAILED with error message."""
        stmt = (
            update(IngestionJobModel)
            .where(IngestionJobModel.id == job_id)
            .values(
                status=IngestionStatus.FAILED,
                completed_at=datetime.now(timezone.utc),
                error_message=error_message,
            )
        )
        result = await session.execute(stmt)
        await session.commit()
        return result.rowcount > 0

# Global instance
ingestion_repo = IngestionRepository()
