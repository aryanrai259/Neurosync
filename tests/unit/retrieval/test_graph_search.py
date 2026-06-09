import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID
from datetime import datetime

from backend.retrieval.graph_search import graph_search, _extract_query_entities
from backend.models.enums import SourceType
from backend.db.models.event import EventModel

pytestmark = pytest.mark.asyncio

@pytest.fixture
def mock_session():
    session = AsyncMock()
    return session

@pytest.fixture
def mock_driver():
    driver = MagicMock()
    graph_session = AsyncMock()
    # Mock context manager
    graph_session.__aenter__.return_value = graph_session
    graph_session.__aexit__.return_value = None
    driver.session.return_value = graph_session
    return driver

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

def test_extract_query_entities():
    # Mock the EntityResolver to avoid real DB calls or heavy logic
    with patch("backend.retrieval.graph_search.EntityResolver") as mock_resolver_cls:
        mock_resolver = MagicMock()
        mock_ref = MagicMock()
        mock_ref.canonical_name = "auth-service"
        mock_resolver.resolve.return_value = [mock_ref]
        mock_resolver_cls.return_value = mock_resolver
        
        entities = _extract_query_entities("Who owns auth-service?")
        assert entities == ["auth-service"]

def test_extract_query_entities_exception():
    with patch("backend.retrieval.graph_search.EntityResolver", side_effect=Exception("Failed")):
        entities = _extract_query_entities("Who owns auth-service?")
        assert entities == []

async def test_graph_search_empty_query(mock_session, mock_driver):
    workspace_id = uuid4()
    results = await graph_search(mock_session, mock_driver, workspace_id, "   ", k=10)
    assert len(results) == 0

@patch("backend.retrieval.graph_search._extract_query_entities", return_value=[])
async def test_graph_search_no_entities(mock_extract, mock_session, mock_driver):
    workspace_id = uuid4()
    results = await graph_search(mock_session, mock_driver, workspace_id, "no entities here", k=10)
    assert len(results) == 0

@patch("backend.retrieval.graph_search._extract_query_entities", return_value=["auth-service"])
@patch("backend.retrieval.graph_search.graph_queries.find_events_by_entity", return_value=[])
async def test_graph_search_no_events_found(mock_find, mock_extract, mock_session, mock_driver):
    workspace_id = uuid4()
    results = await graph_search(mock_session, mock_driver, workspace_id, "query with auth-service", k=10)
    assert len(results) == 0

@patch("backend.retrieval.graph_search._extract_query_entities", return_value=["auth-service"])
@patch("backend.retrieval.graph_search.graph_queries.find_events_by_entity")
async def test_graph_search_success(mock_find, mock_extract, mock_session, mock_driver):
    event_id = uuid4()
    workspace_id = uuid4()
    
    # Mock Neo4j return
    mock_find.return_value = [str(event_id)]
    
    # Mock DB hydration
    mock_event = make_mock_event(event_id)
    mock_result = MagicMock()
    mock_result.scalars().all.return_value = [mock_event]
    mock_session.execute.return_value = mock_result
    
    results = await graph_search(mock_session, mock_driver, workspace_id, "query with auth-service", k=10)
    
    assert len(results) == 1
    assert results[0].event_id == event_id
    assert results[0].graph_score == 1.0
    assert results[0].vector_score == 0.0
    assert results[0].combined_score == 0.3
