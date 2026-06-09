import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID
from datetime import datetime

from backend.retrieval.vector_search import vector_search
from backend.models.enums import SourceType
from backend.db.models.event import EventModel
from backend.db.models.event_embedding import EventEmbeddingModel

pytestmark = pytest.mark.asyncio

@pytest.fixture
def mock_session():
    session = AsyncMock()
    return session

@pytest.fixture
def mock_vector_repo():
    repo = AsyncMock()
    return repo

def make_mock_event(event_id: UUID) -> EventModel:
    return EventModel(
        id=event_id,
        workspace_id=uuid4(),
        source=SourceType.SLACK,
        source_id="test-source",
        content="Test content",
        author_id="user1",
        timestamp=datetime.now()
    )

async def test_vector_search_empty_query(mock_session, mock_vector_repo):
    workspace_id = uuid4()
    results = await vector_search(mock_session, mock_vector_repo, workspace_id, "   ", k=10)
    assert len(results) == 0

@patch("backend.retrieval.vector_search.embed_text")
async def test_vector_search_embedding_fails(mock_embed, mock_session, mock_vector_repo):
    mock_embed.side_effect = Exception("Ollama offline")
    workspace_id = uuid4()
    results = await vector_search(mock_session, mock_vector_repo, workspace_id, "query", k=10)
    assert len(results) == 0

@patch("backend.retrieval.vector_search.embed_text", return_value=[0.1, 0.2, 0.3])
async def test_vector_search_no_hits(mock_embed, mock_session, mock_vector_repo):
    mock_vector_repo.search_similar.return_value = []
    workspace_id = uuid4()
    results = await vector_search(mock_session, mock_vector_repo, workspace_id, "query", k=10)
    assert len(results) == 0

@patch("backend.retrieval.vector_search.embed_text", return_value=[0.1, 0.2, 0.3])
async def test_vector_search_success(mock_embed, mock_session, mock_vector_repo):
    event_id = uuid4()
    workspace_id = uuid4()
    
    # Mock search_similar
    mock_emb_model = EventEmbeddingModel(event_id=event_id, workspace_id=workspace_id)
    mock_vector_repo.search_similar.return_value = [(mock_emb_model, 0.2)] # distance = 0.2
    
    # Mock DB hydration
    mock_event = make_mock_event(event_id)
    mock_result = MagicMock()
    mock_result.scalars().all.return_value = [mock_event]
    mock_session.execute.return_value = mock_result
    
    results = await vector_search(mock_session, mock_vector_repo, workspace_id, "test query", k=10)
    
    assert len(results) == 1
    assert results[0].event_id == event_id
    # distance 0.2 -> similarity 0.9 -> vector_score 0.9 -> combined_score 0.63
    assert results[0].vector_score == 0.9
    assert results[0].combined_score == 0.63
