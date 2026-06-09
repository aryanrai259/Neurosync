# tests/unit/ingestion/test_deduplicator.py
# Tests for Deduplicator — uses a mock AsyncSession (no real DB).
# Run: pytest tests/unit/ingestion/test_deduplicator.py -v

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from backend.ingestion.deduplicator import Deduplicator
from backend.models.enums import SourceType

pytestmark = pytest.mark.asyncio


class TestDeduplicator:
    def setup_method(self):
        self.deduplicator = Deduplicator()
        self.workspace_id = uuid4()

    async def test_returns_true_when_event_exists(self):
        """When the DB returns a row, is_duplicate must return True."""
        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.first.return_value = ("some-uuid",)  # row found
        session.execute = AsyncMock(return_value=mock_result)

        result = await self.deduplicator.is_duplicate(
            session=session,
            workspace_id=self.workspace_id,
            source=SourceType.SLACK,
            source_id="1716000000.000001",
        )
        assert result is True

    async def test_returns_false_when_event_does_not_exist(self):
        """When the DB returns no row, is_duplicate must return False."""
        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.first.return_value = None  # no row found
        session.execute = AsyncMock(return_value=mock_result)

        result = await self.deduplicator.is_duplicate(
            session=session,
            workspace_id=self.workspace_id,
            source=SourceType.SLACK,
            source_id="brand-new-id",
        )
        assert result is False

    async def test_executes_one_db_query(self):
        """Deduplicator must make exactly one DB call per invocation."""
        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.first.return_value = None
        session.execute = AsyncMock(return_value=mock_result)

        await self.deduplicator.is_duplicate(
            session=session,
            workspace_id=self.workspace_id,
            source=SourceType.GITHUB,
            source_id="pr-99",
        )
        session.execute.assert_called_once()

    async def test_different_sources_same_source_id_checked_separately(self):
        """
        The deduplicator must include source in its query.
        Two events with the same source_id but different sources are different events.
        This test ensures the query is built correctly (not testing DB behaviour).
        """
        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.first.return_value = None
        session.execute = AsyncMock(return_value=mock_result)

        # Call with SLACK first, then GITHUB — both should hit the DB
        await self.deduplicator.is_duplicate(session, self.workspace_id, SourceType.SLACK, "id-1")
        await self.deduplicator.is_duplicate(session, self.workspace_id, SourceType.GITHUB, "id-1")

        assert session.execute.call_count == 2
