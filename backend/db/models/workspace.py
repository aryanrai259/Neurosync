# Purpose:      SQLAlchemy model for Workspaces.
#               Maps the pydantic models/workspace.py to PostgreSQL.
# Called By:    repositories/workspace_repo.py
# Dependencies: sqlalchemy

from sqlalchemy import Boolean, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.models.base import Base, TimestampMixin, UUIDMixin


class WorkspaceModel(Base, UUIDMixin, TimestampMixin):
    """
    SQLAlchemy mapping for the workspaces table.
    """

    __tablename__ = "workspaces"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Store the complex WorkspaceConfig as a JSONB column rather than 
    # creating multiple related tables. This perfectly matches our
    # pydantic boundaries and avoids unnecessary joins.
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
