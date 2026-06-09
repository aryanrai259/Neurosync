"""Phase 4B: create event_embeddings table with PgVector HNSW index

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-06-06

Changes:
    1. Enable the pgvector extension (CREATE EXTENSION IF NOT EXISTS vector)
    2. Create event_embeddings table with VECTOR(768) column
    3. Add HNSW index for approximate nearest neighbor search
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

EMBEDDING_DIM = 768
_UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    """Upgrade schema."""
    # ── 1. Enable pgvector extension ─────────────────────────────────────────
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # ── 2. Create event_embeddings table ─────────────────────────────────────
    op.create_table(
        "event_embeddings",
        sa.Column("id", _UUID, nullable=False),
        sa.Column("event_id", _UUID, nullable=False),
        sa.Column("workspace_id", _UUID, nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=False),
        sa.Column("model_name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "event_id", "chunk_index",
            name="uq_event_embeddings_event_chunk",
        ),
    )
    op.create_index(
        op.f("ix_event_embeddings_id"),
        "event_embeddings",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_event_embeddings_event_id"),
        "event_embeddings",
        ["event_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_event_embeddings_workspace_id"),
        "event_embeddings",
        ["workspace_id"],
        unique=False,
    )

    # ── 3. HNSW index for cosine similarity ──────────────────────────────────
    # HNSW provides approximate nearest neighbor with very fast query times.
    # m=16 and ef_construction=64 are good defaults for recall/speed balance.
    op.execute(
        "CREATE INDEX ix_event_embeddings_hnsw "
        "ON event_embeddings "
        "USING hnsw (embedding vector_cosine_ops) "
        "WITH (m=16, ef_construction=64)"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP INDEX IF EXISTS ix_event_embeddings_hnsw")
    op.drop_index(op.f("ix_event_embeddings_workspace_id"), table_name="event_embeddings")
    op.drop_index(op.f("ix_event_embeddings_event_id"), table_name="event_embeddings")
    op.drop_index(op.f("ix_event_embeddings_id"), table_name="event_embeddings")
    op.drop_table("event_embeddings")
    # Note: we intentionally leave the vector extension in place on downgrade
    # to avoid breaking any other tables that might use it.
