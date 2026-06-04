# Purpose:      SQLAlchemy model for Workspace Snapshots (long-term memory).
#               Maps the WorkspaceSnapshot pydantic model to PostgreSQL.
#               SessionContext is excluded as it lives purely in Redis.
# Called By:    repositories/memory_repo.py
# Dependencies: sqlalchemy

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.models.base import GUID, Base, TimestampMixin, UUIDMixin


class WorkspaceSnapshotModel(Base, UUIDMixin, TimestampMixin):
    """
    SQLAlchemy mapping for the workspace_snapshots table.
    Stores the long-term knowledge synthesized by the LLM about a workspace.
    """

    __tablename__ = "workspace_snapshots"

    workspace_id: Mapped[UUID] = mapped_column(GUID(), unique=True, index=True, nullable=False)
    
    # Store lists as JSONB arrays
    key_decisions: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    active_entities: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    event_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_ingestion_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
