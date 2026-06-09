# Purpose:      SQLAlchemy model for the memory_objects table.
#               Stores the structured extraction result (entities + relationships)
#               for each ingested event. Write-once. Used for replay and debugging.
#               The MemoryObject Pydantic model in memory/memory_object.py is
#               the in-memory representation; this is the persistence layer.
# Called By:    db/repositories/memory_repo.py
# Dependencies: sqlalchemy, backend/db/models/base.py
# Test File:    tests/integration/memory/test_memory_constructor.py

from uuid import UUID

from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.models.base import GUID, Base, TimestampMixin, UUIDMixin


class MemoryObjectModel(Base, UUIDMixin, TimestampMixin):
    """
    Persistence model for MemoryObject extraction results.

    Stores the entities and relationships extracted from one event as JSONB.
    This is a write-once audit log — never updated after insert.
    Deleting and re-inserting is the correct replay pattern.

    Columns:
        event_id:      FK to events.id. One row per event.
        workspace_id:  Workspace scoping for efficient querying.
        entities:      JSON array of EntityRef dicts.
        relationships: JSON array of RelationshipRef dicts.
    """

    __tablename__ = "memory_objects"

    event_id: Mapped[UUID] = mapped_column(
        GUID(),
        nullable=False,
        index=True,
        unique=True,   # One memory object per event
        comment="FK → events.id. Provenance anchor.",
    )
    workspace_id: Mapped[UUID] = mapped_column(
        GUID(),
        nullable=False,
        index=True,
    )
    entities: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        comment="Serialized list of EntityRef dicts.",
    )
    relationships: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        comment="Serialized list of RelationshipRef dicts.",
    )
