# Purpose:      SQLAlchemy model for Entity Registry.
#               Authoritative source of truth for entities. Neo4j acts as a 
#               projection/relationship engine built on top of this.
# Called By:    repositories/entity_registry_repo.py
# Dependencies: sqlalchemy

from uuid import UUID

from sqlalchemy import Enum, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.models.base import GUID, Base, TimestampMixin, UUIDMixin
from backend.models.enums import EntityType, SyncStatus


class EntityRegistryModel(Base, UUIDMixin, TimestampMixin):
    """
    SQLAlchemy mapping for the entity_registry table.
    Ensures canonical existence of entities even if Neo4j is rebuilt.
    """

    __tablename__ = "entity_registry"

    workspace_id: Mapped[UUID] = mapped_column(GUID(), index=True, nullable=False)
    
    entity_type: Mapped[EntityType] = mapped_column(Enum(EntityType), nullable=False)
    canonical_name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    graph_sync_status: Mapped[SyncStatus] = mapped_column(
        Enum(SyncStatus), 
        default=SyncStatus.PENDING,
        nullable=False,
        index=True
    )
    
    source_event_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    __table_args__ = (
        # Ensure only one entity of a given type/name per workspace
        UniqueConstraint(
            "workspace_id", "entity_type", "canonical_name", 
            name="uq_entity_registry_workspace_type_name"
        ),
    )
