# Purpose:      SQLAlchemy model for Ingestion Jobs.
#               Combines IngestionRequest and IngestionResult into one table.
# Called By:    repositories/ingestion_repo.py
# Dependencies: sqlalchemy

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Enum, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.models.base import GUID, Base, TimestampMixin, UUIDMixin
from backend.models.enums import IngestionStatus, SourceType


class IngestionJobModel(Base, UUIDMixin, TimestampMixin):
    """
    SQLAlchemy mapping for the ingestion_jobs table.
    Tracks the lifecycle of an ingestion run from request through completion.
    """

    __tablename__ = "ingestion_jobs"

    workspace_id: Mapped[UUID] = mapped_column(GUID(), index=True, nullable=False)
    
    source: Mapped[SourceType] = mapped_column(Enum(SourceType), nullable=False)
    source_config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    
    requested_by: Mapped[str] = mapped_column(String(255), nullable=False)
    
    status: Mapped[IngestionStatus] = mapped_column(
        Enum(IngestionStatus), 
        default=IngestionStatus.PENDING,
        nullable=False,
        index=True
    )
    
    events_ingested: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    events_failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    processing_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
