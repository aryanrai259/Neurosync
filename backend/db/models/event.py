# Purpose:      SQLAlchemy model for Events.
#               Maps the pydantic models/event.py to PostgreSQL.
# Called By:    repositories/event_repo.py
# Dependencies: sqlalchemy

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Enum, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.models.base import GUID, Base, TimestampMixin, UUIDMixin
from backend.models.enums import EmbeddingStatus, SourceType


class EventModel(Base, UUIDMixin, TimestampMixin):
    """
    SQLAlchemy mapping for the events table.
    Stores the canonical records of data from all source systems.
    """

    __tablename__ = "events"

    workspace_id: Mapped[UUID] = mapped_column(GUID(), index=True, nullable=False)
    
    source: Mapped[SourceType] = mapped_column(Enum(SourceType), nullable=False)
    source_id: Mapped[str] = mapped_column(String(255), nullable=False)
    
    content: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    author_id: Mapped[str] = mapped_column(String(255), nullable=False)
    author_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    metadata_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    
    embedding_status: Mapped[EmbeddingStatus] = mapped_column(
        Enum(EmbeddingStatus), 
        default=EmbeddingStatus.PENDING,
        nullable=False,
        index=True
    )

    __table_args__ = (
        # Prevent double ingestion of the same event
        UniqueConstraint(
            "workspace_id", "source", "source_id", 
            name="uq_events_workspace_source_id"
        ),
    )
