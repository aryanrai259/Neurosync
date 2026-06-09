# Purpose:      SQLAlchemy ORM model for API keys.
#               Maps the api_keys table — created by migration d7e8f9a0b1c2.
#               API keys are workspace-scoped, stored as SHA-256 hashes.
#               The raw key is shown to the user ONCE at creation time; only
#               the hash is persisted so stolen DB access cannot expose keys.
# Called By:    db/repositories/api_key_repo.py
# Dependencies: sqlalchemy
# Test File:    tests/unit/db/test_api_key_model.py

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.models.base import Base, TimestampMixin, UUIDMixin


class ApiKeyModel(Base, UUIDMixin, TimestampMixin):
    """
    SQLAlchemy mapping for the api_keys table.

    An API key is workspace-scoped. The raw key (cb_xxxx) is shown
    once at generation time. Only the SHA-256 hash is persisted.
    """

    __tablename__ = "api_keys"

    workspace_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # SHA-256 hex digest of the raw key — used for constant-time lookup
    key_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
    )

    # Human-readable label for the key (e.g. "CI pipeline", "frontend")
    label: Mapped[str] = mapped_column(String(255), nullable=False, default="default")

    # Soft-delete: revoked keys remain in DB for audit trail
    is_active: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)

    # Optional expiry — None means no expiry
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Last time this key was used — updated on each successful auth
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
