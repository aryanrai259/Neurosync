"""phase6_decisions_and_timeline

Revision ID: c6d7e8f9a0b1
Revises: f80f6fdc088a

Adds:
- decisions table (MVP decision intelligence store)
"""
from typing import Sequence, Union
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = 'c6d7e8f9a0b1'
down_revision: Union[str, Sequence[str], None] = 'f80f6fdc088a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -----------------------------------------------------------------
    # decisions table
    # -----------------------------------------------------------------
    op.create_table(
        'decisions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('title', sa.String(512), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(64), nullable=False, server_default='ACTIVE', index=True),
        sa.Column('decision_date', sa.DateTime(timezone=True), nullable=True, index=True),
        sa.Column('decided_by', sa.String(255), nullable=True),
        sa.Column('supersedes_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('source_event_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('events.id', ondelete='SET NULL'), nullable=True),
        sa.Column('metadata_', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
    )


def downgrade() -> None:
    op.drop_table('decisions')
