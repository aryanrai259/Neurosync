# Purpose:      SQLAlchemy ORM model for organizational decisions.
#               Maps the decisions table — created by migration c6d7e8f9a0b1.
#               A Decision captures the outcome of a deliberation, the party
#               that made it, when it was made, and optionally which prior
#               decision it supersedes.
# Called By:    db/repositories/decision_repo.py, reasoning/decision_module.py
# Dependencies: sqlalchemy
# Test File:    tests/integration/db/test_decision_repo.py

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.models.base import Base, TimestampMixin, UUIDMixin


class DecisionModel(Base, UUIDMixin, TimestampMixin):
    """
    SQLAlchemy mapping for the decisions table.

    A decision is an organizational artifact: a statement that something was
    decided, by whom, when, and (optionally) which prior decision it replaces.
    """

    __tablename__ = "decisions"

    workspace_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(String(512), nullable=False)

    description: Mapped[str | None] = mapped_column(Text(), nullable=True)

    # ACTIVE | SUPERSEDED | REVERTED | DRAFT
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="ACTIVE")

    decision_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    decided_by: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # UUID of the decision this supersedes (self-referential, not FK to keep it simple)
    supersedes_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True
    )

    # Optional link to the source event where this decision was extracted from
    source_event_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("events.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Arbitrary structured metadata (tags, links, context)
    metadata_: Mapped[dict] = mapped_column(JSONB(), nullable=False, default=dict)
