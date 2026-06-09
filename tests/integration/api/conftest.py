"""Shared fixtures for API integration tests."""
import pytest
import pytest_asyncio
from uuid import uuid4

from backend.db.session import async_session
from backend.db.repositories.workspace_repo import workspace_repo


@pytest_asyncio.fixture(scope="module")
async def test_workspace_id():
    """Create a test workspace and return its UUID. Shared across the test module."""
    async with async_session() as session:
        ws = await workspace_repo.create(session, name=f"api-test-workspace-{uuid4().hex[:6]}")
        await session.commit()
        await session.refresh(ws)
        return ws.id
