import pytest
import pytest_asyncio
from uuid import uuid4, UUID
import os
from unittest.mock import patch, AsyncMock, MagicMock

from backend.reasoning.pipeline import pipeline
from backend.core.config import get_settings
from backend.retrieval.schemas import RetrievedChunk
from backend.models.enums import SourceType
from datetime import datetime

pytestmark = pytest.mark.asyncio

@pytest_asyncio.fixture(autouse=True)
def setup_mock_llm():
    with patch("backend.reasoning.composer.llm_client.provider", "mock"):
        yield

@pytest.fixture(autouse=True)
def mock_db():
    # Mock the async_session context manager
    mock_session = AsyncMock()
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__.return_value = None

    # Mock the driver
    mock_driver = MagicMock()

    with patch("backend.reasoning.pipeline.async_session", return_value=mock_session), \
         patch("backend.reasoning.pipeline.get_driver", return_value=mock_driver), \
         patch("backend.reasoning.pipeline.config_repo.get_known_entities", return_value=["auth-service"]):
        yield mock_session

@pytest.fixture
def mock_retrieval():
    with patch("backend.reasoning.pipeline.vector_search") as mock_vector, \
         patch("backend.reasoning.pipeline.graph_search") as mock_graph:
        
        mock_chunk = RetrievedChunk(
            event_id=UUID("123e4567-e89b-12d3-a456-426614174000"),
            content="Auth service is owned by Platform Team.",
            source=SourceType.SLACK,
            timestamp=datetime.now(),
            author_id="user1"
        )
        
        async def mock_search(session, repo_or_driver, workspace_id, query, k):
            if not query or not query.strip():
                return []
            return [mock_chunk]
            
        mock_vector.side_effect = mock_search
        mock_graph.side_effect = mock_search
        yield mock_vector, mock_graph

async def test_empty_query(mock_retrieval):
    workspace_id = uuid4()
    # pipeline should handle empty gracefully
    answer = await pipeline.query("", workspace_id)
    assert answer.retrieval_strategy == "HYBRID"
    assert answer.confidence == "LOW"

async def test_whitespace_query(mock_retrieval):
    workspace_id = uuid4()
    answer = await pipeline.query("   ", workspace_id)
    assert answer.retrieval_strategy == "HYBRID"
    assert answer.confidence == "LOW"

async def test_unknown_entity(mock_retrieval):
    workspace_id = uuid4()
    answer = await pipeline.query("What does unknown-service do?", workspace_id)
    # Because it lacks structural/hybrid keywords, should route to VECTOR_ONLY
    assert answer.retrieval_strategy == "VECTOR_ONLY"

async def test_ownership_question(mock_retrieval):
    workspace_id = uuid4()
    with patch("backend.reasoning.pipeline.config_repo.get_known_entities", return_value=["auth-service"]):
        answer = await pipeline.query("Who owns auth-service?", workspace_id)
    assert answer.retrieval_strategy == "GRAPH_ONLY"

async def test_dependency_question(mock_retrieval):
    workspace_id = uuid4()
    with patch("backend.reasoning.pipeline.config_repo.get_known_entities", return_value=["auth-service"]):
        answer = await pipeline.query("What depends on auth-service?", workspace_id)
    assert answer.retrieval_strategy == "GRAPH_ONLY"

async def test_hybrid_question(mock_retrieval):
    workspace_id = uuid4()
    answer = await pipeline.query("What recently broke auth-service?", workspace_id)
    assert answer.retrieval_strategy == "HYBRID"

async def test_malformed_citations():
    from backend.reasoning.citation import citation_validator
    
    proposed = ["invalid-uuid", "123e4567-e89b-12d3-a456-426614174000"]
    chunk = RetrievedChunk(
        event_id=UUID("123e4567-e89b-12d3-a456-426614174000"),
        content="test",
        source=SourceType.SLACK,
        timestamp=datetime.now(),
        author_id="user1"
    )
    
    valid, conf = citation_validator.validate(proposed, [chunk])
    assert "invalid-uuid" not in valid
    assert "123e4567-e89b-12d3-a456-426614174000" in valid

async def test_hallucinated_citations():
    from backend.reasoning.citation import citation_validator
    
    proposed = ["11111111-1111-1111-1111-111111111111"]
    chunk = RetrievedChunk(
        event_id=UUID("22222222-2222-2222-2222-222222222222"),
        content="test",
        source=SourceType.SLACK,
        timestamp=datetime.now(),
        author_id="user1"
    )
    
    valid, conf = citation_validator.validate(proposed, [chunk])
    assert len(valid) == 0
    assert conf == "LOW"

async def test_very_large_query(mock_retrieval):
    workspace_id = uuid4()
    query = "error " * 1000
    answer = await pipeline.query(query, workspace_id)
    assert answer.retrieval_strategy == "HYBRID"

