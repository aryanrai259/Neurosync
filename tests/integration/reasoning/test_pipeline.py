import pytest
import pytest_asyncio
from uuid import uuid4
import os

from backend.reasoning.pipeline import pipeline
from backend.core.config import get_settings

pytestmark = pytest.mark.asyncio

@pytest_asyncio.fixture(autouse=True)
def setup_mock_llm():
    # Force the mock provider for tests
    os.environ["LLM_PROVIDER"] = "mock"
    get_settings.cache_clear()
    yield

async def test_empty_query():
    workspace_id = uuid4()
    # pipeline should handle empty gracefully
    answer = await pipeline.query("", workspace_id)
    assert answer.retrieval_strategy == "UNKNOWN"
    assert answer.confidence == "LOW"

async def test_whitespace_query():
    workspace_id = uuid4()
    answer = await pipeline.query("   ", workspace_id)
    assert answer.retrieval_strategy == "UNKNOWN"

async def test_unknown_entity():
    workspace_id = uuid4()
    answer = await pipeline.query("What does unknown-service do?", workspace_id)
    # Because it lacks structural/hybrid keywords, should route to VECTOR_ONLY
    assert answer.retrieval_strategy == "VECTOR_ONLY"

async def test_ownership_question():
    workspace_id = uuid4()
    answer = await pipeline.query("Who owns auth-service?", workspace_id)
    # 'who owns' is structural keyword, 'auth-service' is known (mocked in pipeline.py)
    assert answer.retrieval_strategy == "GRAPH_ONLY"

async def test_dependency_question():
    workspace_id = uuid4()
    answer = await pipeline.query("What depends on auth-service?", workspace_id)
    assert answer.retrieval_strategy == "GRAPH_ONLY"

async def test_hybrid_question():
    workspace_id = uuid4()
    answer = await pipeline.query("What recently broke auth-service?", workspace_id)
    # 'recently' is a hybrid keyword
    assert answer.retrieval_strategy == "HYBRID"

async def test_malformed_citations():
    # Since we use a mocked LLM returning a valid citation, this test would require
    # patching the LLM client or testing CitationValidator directly.
    from backend.reasoning.citation import citation_validator
    
    proposed = ["[invalid-uuid]", "[123e4567-e89b-12d3-a456-426614174000]"]
    retrieved = [{"id": "123e4567-e89b-12d3-a456-426614174000"}]
    
    valid, conf = citation_validator.validate(proposed, retrieved)
    assert "invalid-uuid" not in valid
    assert "123e4567-e89b-12d3-a456-426614174000" in valid

async def test_hallucinated_citations():
    from backend.reasoning.citation import citation_validator
    
    proposed = ["11111111-1111-1111-1111-111111111111"]
    retrieved = [{"id": "22222222-2222-2222-2222-222222222222"}]
    
    valid, conf = citation_validator.validate(proposed, retrieved)
    assert len(valid) == 0
    assert conf == "LOW"

async def test_very_large_query():
    workspace_id = uuid4()
    query = "error " * 1000
    answer = await pipeline.query(query, workspace_id)
    assert answer.retrieval_strategy == "HYBRID"
