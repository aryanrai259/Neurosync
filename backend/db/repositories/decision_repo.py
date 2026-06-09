# Purpose:      Decision repository — CRUD and query operations for the decisions table.
# Called By:    reasoning/decision_module.py, api/v1/decisions.py
# Calls:        db/models/decision.py
# Dependencies: sqlalchemy
# Test File:    tests/integration/db/test_decision_repo.py

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models.decision import DecisionModel
from backend.db.repositories.base import BaseRepository


class DecisionRepository(BaseRepository[DecisionModel]):
    """Repository for DecisionModel — stores and queries organizational decisions."""

    def __init__(self) -> None:
        super().__init__(DecisionModel)

    async def create_decision(
        self,
        session: AsyncSession,
        workspace_id: UUID,
        title: str,
        description: str | None = None,
        status: str = "ACTIVE",
        decision_date: datetime | None = None,
        decided_by: str | None = None,
        supersedes_id: UUID | None = None,
        source_event_id: UUID | None = None,
        metadata: dict | None = None,
    ) -> DecisionModel:
        """
        Persist a new decision.
        Auto-commits; caller can commit again (no-op).
        """
        decision = DecisionModel(
            workspace_id=workspace_id,
            title=title,
            description=description,
            status=status,
            decision_date=decision_date or datetime.now(timezone.utc),
            decided_by=decided_by,
            supersedes_id=supersedes_id,
            source_event_id=source_event_id,
            metadata_=metadata or {},
        )
        session.add(decision)
        await session.flush()
        await session.commit()
        await session.refresh(decision)

        # If this supersedes another decision, mark it SUPERSEDED
        if supersedes_id:
            old = await self.get_by_id(session, supersedes_id)
            if old:
                old.status = "SUPERSEDED"
                await session.commit()

        return decision

    async def list_for_workspace(
        self,
        session: AsyncSession,
        workspace_id: UUID,
        status: str | None = None,
        limit: int = 50,
    ) -> list[DecisionModel]:
        """
        List decisions for a workspace.
        Optionally filter by status (ACTIVE, SUPERSEDED, REVERTED, DRAFT).
        Results ordered by decision_date descending.
        """
        stmt = (
            select(DecisionModel)
            .where(DecisionModel.workspace_id == workspace_id)
        )
        if status:
            stmt = stmt.where(DecisionModel.status == status)
        stmt = stmt.order_by(DecisionModel.decision_date.desc()).limit(limit)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_active_decisions(
        self, session: AsyncSession, workspace_id: UUID
    ) -> list[DecisionModel]:
        """Return only ACTIVE decisions for a workspace."""
        return await self.list_for_workspace(session, workspace_id, status="ACTIVE")

    async def search_by_title(
        self, session: AsyncSession, workspace_id: UUID, query: str
    ) -> list[DecisionModel]:
        """
        Full-text search on decision titles using ILIKE.
        Returns all decisions (any status) where title contains query string.
        """
        stmt = (
            select(DecisionModel)
            .where(DecisionModel.workspace_id == workspace_id)
            .where(DecisionModel.title.ilike(f"%{query}%"))
            .order_by(DecisionModel.decision_date.desc())
            .limit(20)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())


# Global instance
decision_repo = DecisionRepository()
