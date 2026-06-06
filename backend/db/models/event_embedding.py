# Purpose:      SQLAlchemy model for the event_embeddings table.
#               One row per event (one embedding chunk per event in Phase 4).
#               Stores the vector embedding alongside its provenance:
#               event_id, workspace_id, model_name.
#               Phase 5+ can extend chunk_index for multi-chunk support.
# Called By:    db/repositories/vector_repo.py
# Dependencies: sqlalchemy, pgvector
# Test File:    tests/integration/memory/test_vector_indexer.py

from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.models.base import GUID, Base, TimestampMixin, UUIDMixin
from backend.memory.embeddings import EMBEDDING_DIM


class EventEmbeddingModel(Base, UUIDMixin, TimestampMixin):
    """
    Persistence model for event_embeddings table.

    Stores one vector embedding per event. chunk_index is always 0 in Phase 4
    (single-chunk per event). A future migration can support multiple chunks
    by removing the unique constraint on (event_id) and allowing chunk_index > 0.

    The embedding column uses pgvector's Vector type with HNSW indexing
    (defined in the Alembic migration, not here).
    """

    __tablename__ = "event_embeddings"

    event_id: Mapped[UUID] = mapped_column(
        GUID(),
        nullable=False,
        index=True,
        comment="FK → events.id. Provenance anchor.",
    )
    workspace_id: Mapped[UUID] = mapped_column(
        GUID(),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Chunk index within this event. Always 0 in Phase 4.",
    )
    embedding: Mapped[list[float]] = mapped_column(
        Vector(EMBEDDING_DIM),
        nullable=False,
        comment=f"Vector embedding ({EMBEDDING_DIM} dims, nomic-embed-text).",
    )
    model_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Embedding model used to generate this vector.",
    )

    __table_args__ = (
        UniqueConstraint(
            "event_id", "chunk_index",
            name="uq_event_embeddings_event_chunk",
        ),
    )
