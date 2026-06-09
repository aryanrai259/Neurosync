# Purpose:      SQLAlchemy models for the Configuration Registry (Phase 5).
#               Provides authoritative mappings for teams, services, repos, and dependencies.
# Called By:    repositories/config_repo.py
# Dependencies: sqlalchemy

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.models.base import GUID, Base, TimestampMixin, UUIDMixin


class ConfigRegistryVersionModel(Base, UUIDMixin):
    """
    Tracks the version of the configuration registry.
    Incremented on every CRUD operation to support Neo4j sync state tracking.
    """
    __tablename__ = "config_registry_version"

    workspace_id: Mapped[UUID] = mapped_column(GUID(), index=True, unique=True, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class ConfigTeamModel(Base, UUIDMixin, TimestampMixin):
    """
    Authoritative representation of an organizational team.
    """
    __tablename__ = "config_teams"

    workspace_id: Mapped[UUID] = mapped_column(GUID(), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("workspace_id", "name", name="uq_config_teams_workspace_name"),
    )


class ConfigServiceModel(Base, UUIDMixin, TimestampMixin):
    """
    Authoritative representation of a software service.
    """
    __tablename__ = "config_services"

    workspace_id: Mapped[UUID] = mapped_column(GUID(), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    __table_args__ = (
        UniqueConstraint("workspace_id", "name", name="uq_config_services_workspace_name"),
    )


class ConfigRepositoryModel(Base, UUIDMixin, TimestampMixin):
    """
    Maps source repositories to the services they belong to.
    Many Repositories -> 1 Service.
    """
    __tablename__ = "config_repositories"

    workspace_id: Mapped[UUID] = mapped_column(GUID(), index=True, nullable=False)
    repo_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    
    service_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("config_services.id", ondelete="CASCADE"), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("workspace_id", "repo_url", name="uq_config_repos_workspace_url"),
    )


class ConfigOwnershipModel(Base):
    """
    Team -> OWNS -> Service mapping.
    """
    __tablename__ = "config_ownership"

    team_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("config_teams.id", ondelete="CASCADE"), primary_key=True
    )
    service_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("config_services.id", ondelete="CASCADE"), primary_key=True
    )
    workspace_id: Mapped[UUID] = mapped_column(GUID(), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )


class ConfigDependencyModel(Base):
    """
    Service -> DEPENDS_ON -> Service mapping.
    """
    __tablename__ = "config_dependencies"

    service_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("config_services.id", ondelete="CASCADE"), primary_key=True
    )
    depends_on_service_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("config_services.id", ondelete="CASCADE"), primary_key=True
    )
    workspace_id: Mapped[UUID] = mapped_column(GUID(), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
