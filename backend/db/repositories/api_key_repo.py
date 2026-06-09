# Purpose:      API key repository — CRUD and lookup operations for the api_keys table.
#               Central point for key creation, revocation, and hash-based lookup.
#               All auth decisions go through api_key_repo.get_by_hash().
# Called By:    api/middleware/auth.py, api/v1/auth.py
# Calls:        db/models/api_key.py
# Dependencies: sqlalchemy
# Test File:    tests/unit/db/test_api_key_repo.py

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models.api_key import ApiKeyModel
from backend.db.repositories.base import BaseRepository


class ApiKeyRepository(BaseRepository[ApiKeyModel]):
    """Repository for ApiKeyModel — key creation, lookup by hash, revocation."""

    def __init__(self) -> None:
        super().__init__(ApiKeyModel)

    async def create_key(
        self,
        session: AsyncSession,
        workspace_id: UUID,
        key_hash: str,
        label: str = "default",
        expires_at: datetime | None = None,
    ) -> ApiKeyModel:
        """
        Persist a new API key (hash only — raw key must be shown to user by caller).

        Args:
            session:      Active async DB session.
            workspace_id: Workspace this key belongs to.
            key_hash:     SHA-256 hex digest of the raw key.
            label:        Human-readable name (e.g. 'CI pipeline').
            expires_at:   Optional expiry timestamp. None = never expires.

        Returns:
            Newly created ApiKeyModel with DB-assigned UUID.
        """
        api_key = ApiKeyModel(
            workspace_id=workspace_id,
            key_hash=key_hash,
            label=label,
            is_active=True,
            expires_at=expires_at,
        )
        session.add(api_key)
        await session.flush()
        await session.commit()
        await session.refresh(api_key)
        return api_key

    async def get_by_hash(
        self, session: AsyncSession, key_hash: str
    ) -> ApiKeyModel | None:
        """
        Look up an API key by its SHA-256 hash.

        This is the hot path for every authenticated request — runs a single
        indexed SELECT on key_hash (unique B-tree index).

        Returns:
            The ApiKeyModel if found and active, else None.
        """
        stmt = (
            select(ApiKeyModel)
            .where(ApiKeyModel.key_hash == key_hash)
            .where(ApiKeyModel.is_active.is_(True))
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_workspace(
        self, session: AsyncSession, workspace_id: UUID
    ) -> list[ApiKeyModel]:
        """Return all API keys for a workspace (active and revoked)."""
        stmt = (
            select(ApiKeyModel)
            .where(ApiKeyModel.workspace_id == workspace_id)
            .order_by(ApiKeyModel.created_at.desc())
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def revoke(
        self, session: AsyncSession, key_id: UUID
    ) -> bool:
        """
        Soft-delete: set is_active=False. Key record is preserved for audit.

        Returns:
            True if revoked, False if key_id not found.
        """
        key = await self.get_by_id(session, key_id)
        if key is None:
            return False
        key.is_active = False
        await session.commit()
        return True

    async def touch_last_used(
        self, session: AsyncSession, key_id: UUID
    ) -> None:
        """
        Update last_used_at to now. Called on each successful auth.
        Fire-and-forget — caller should NOT await the result in the hot path.
        """
        key = await self.get_by_id(session, key_id)
        if key:
            key.last_used_at = datetime.now(timezone.utc)
            await session.commit()


# Global instance
api_key_repo = ApiKeyRepository()
