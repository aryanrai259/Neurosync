"""Phase 4A: add aliases to entity_registry, add memory_objects table

Revision ID: a1b2c3d4e5f6
Revises: 2608d658dbcb
Create Date: 2026-06-06

Changes:
    1. entity_registry: add aliases JSONB column (default=[])
    2. Create memory_objects table with event_id FK, entities JSONB, relationships JSONB
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "2608d658dbcb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Reusable PostgreSQL UUID column type
_UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    """Upgrade schema."""
    # ── 1. Add aliases column to entity_registry ──────────────────────────────
    op.add_column(
        "entity_registry",
        sa.Column(
            "aliases",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
            comment="Alternative names this entity is known by. Used for resolution lookup.",
        ),
    )

    # ── 2. Create memory_objects table ────────────────────────────────────────────────
    op.create_table(
        "memory_objects",
        sa.Column("id", _UUID, nullable=False),
        sa.Column("event_id", _UUID, nullable=False),
        sa.Column("workspace_id", _UUID, nullable=False),
        sa.Column(
            "entities",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "relationships",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id", name="uq_memory_objects_event_id"),
    )
    op.create_index(
        op.f("ix_memory_objects_id"),
        "memory_objects",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_memory_objects_event_id"),
        "memory_objects",
        ["event_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_memory_objects_workspace_id"),
        "memory_objects",
        ["workspace_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop memory_objects table
    op.drop_index(op.f("ix_memory_objects_workspace_id"), table_name="memory_objects")
    op.drop_index(op.f("ix_memory_objects_event_id"), table_name="memory_objects")
    op.drop_index(op.f("ix_memory_objects_id"), table_name="memory_objects")
    op.drop_table("memory_objects")

    # Remove aliases column from entity_registry
    op.drop_column("entity_registry", "aliases")
