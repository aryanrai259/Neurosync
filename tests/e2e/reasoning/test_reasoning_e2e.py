import pytest
import pytest_asyncio
from uuid import uuid4, UUID
from datetime import datetime, timezone
from unittest.mock import patch

from backend.reasoning.pipeline import pipeline
from backend.db.session import async_session
from backend.db.models.event import EventModel
from backend.db.models.event_embedding import EventEmbeddingModel
from backend.db.models.config import ConfigServiceModel
from backend.models.enums import SourceType
from backend.graph.client import get_driver

pytestmark = [
    pytest.mark.asyncio(loop_scope="module"),
]

@pytest_asyncio.fixture(autouse=True)
def setup_mock_llm():
    # Only LLM is mocked
    with patch("backend.reasoning.composer.llm_client.provider", "mock"):
        yield

@pytest_asyncio.fixture(loop_scope="module")
async def setup_e2e_data():
    workspace_id = uuid4()
    event_id1 = UUID("123e4567-e89b-12d3-a456-426614174000")
    event_id2 = uuid4()
    event_id3 = uuid4()
    
    # 1. Insert DB
    async with async_session() as session:
        from sqlalchemy import text
        # Pre-cleanup hardcoded event ID to prevent IntegrityError on dirty DB
        await session.execute(text("DELETE FROM event_embeddings WHERE event_id = '123e4567-e89b-12d3-a456-426614174000'"))
        await session.execute(text("DELETE FROM events WHERE id = '123e4567-e89b-12d3-a456-426614174000'"))
        await session.commit()
        
        # Service
        svc = ConfigServiceModel(id=uuid4(), workspace_id=workspace_id, name="auth-service")
        session.add(svc)
        
        # Events
        e1 = EventModel(
            id=event_id1,
            workspace_id=workspace_id,
            source=SourceType.SLACK,
            source_id="slack-1",
            content="Auth service is owned by Platform Team.",
            author_id="user1",
            timestamp=datetime.now(timezone.utc)
        )
        e2 = EventModel(
            id=event_id2,
            workspace_id=workspace_id,
            source=SourceType.GITHUB,
            source_id="github-1",
            content="Recent PR 123 broke auth-service login failures.",
            author_id="user2",
            timestamp=datetime.now(timezone.utc)
        )
        e3 = EventModel(
            id=event_id3,
            workspace_id=workspace_id,
            source=SourceType.JIRA,
            source_id="jira-1",
            content="Outage around login failures yesterday.",
            author_id="user3",
            timestamp=datetime.now(timezone.utc)
        )
        session.add(e1)
        session.add(e2)
        session.add(e3)
        
        # Embeddings (mock PgVector data)
        # Using [0.1]*768 so we can predictably hit it by mocking embed_text
        emb1 = EventEmbeddingModel(
            event_id=event_id1, workspace_id=workspace_id, model_name="test", chunk_index=0,
            embedding=[0.1] * 768
        )
        emb2 = EventEmbeddingModel(
            event_id=event_id2, workspace_id=workspace_id, model_name="test", chunk_index=0,
            embedding=[0.1] * 768
        )
        emb3 = EventEmbeddingModel(
            event_id=event_id3, workspace_id=workspace_id, model_name="test", chunk_index=0,
            embedding=[0.1] * 768
        )
        session.add(emb1)
        session.add(emb2)
        session.add(emb3)
        await session.commit()
        
    # 2. Insert Graph
    driver = get_driver()
    async with driver.session() as graph_session:
        for eid in [event_id1, event_id2, event_id3]:
            await graph_session.run(
                "MERGE (e:Event {event_id: $eid}) "
                "MERGE (s:Service {canonical_name: 'auth-service', workspace_id: $wid}) "
                "MERGE (e)-[:REFERENCES]->(s)",
                eid=str(eid), wid=str(workspace_id)
            )

    yield workspace_id

    # Cleanup DB
    async with async_session() as session:
        from sqlalchemy import text
        await session.execute(text("DELETE FROM event_embeddings WHERE workspace_id = :w"), {"w": workspace_id})
        await session.execute(text("DELETE FROM events WHERE workspace_id = :w"), {"w": workspace_id})
        await session.execute(text("DELETE FROM config_services WHERE workspace_id = :w"), {"w": workspace_id})
        await session.commit()
        
    # Cleanup Graph
    async with driver.session() as graph_session:
        await graph_session.run("MATCH (n {workspace_id: $wid}) DETACH DELETE n", wid=str(workspace_id))
        await graph_session.run("MATCH (e:Event) WHERE e.event_id IN [$e1, $e2, $e3] DETACH DELETE e", 
                                e1=str(event_id1), e2=str(event_id2), e3=str(event_id3))

@patch("backend.retrieval.vector_search.embed_text", return_value=[0.1]*768)
async def test_reasoning_e2e_ownership(mock_embed, setup_e2e_data):
    workspace_id = setup_e2e_data
    answer = await pipeline.query("Who owns auth-service?", workspace_id)
    assert answer.retrieval_strategy == "GRAPH_ONLY"
    assert answer.confidence in ["HIGH", "MEDIUM"]
    assert len(answer.citations) > 0

@patch("backend.retrieval.vector_search.embed_text", return_value=[0.1]*768)
async def test_reasoning_e2e_dependencies(mock_embed, setup_e2e_data):
    workspace_id = setup_e2e_data
    answer = await pipeline.query("What depends on auth-service?", workspace_id)
    assert answer.retrieval_strategy == "GRAPH_ONLY"
    assert len(answer.citations) > 0

@patch("backend.retrieval.vector_search.embed_text", return_value=[0.1]*768)
async def test_reasoning_e2e_hybrid_pr(mock_embed, setup_e2e_data):
    workspace_id = setup_e2e_data
    answer = await pipeline.query("What PRs affected auth-service recently?", workspace_id)
    assert answer.retrieval_strategy == "HYBRID"
    assert len(answer.citations) > 0

@patch("backend.retrieval.vector_search.embed_text", return_value=[0.1]*768)
async def test_reasoning_e2e_hybrid_outages(mock_embed, setup_e2e_data):
    workspace_id = setup_e2e_data
    answer = await pipeline.query("What outages happened around auth-service login failures?", workspace_id)
    assert answer.retrieval_strategy == "HYBRID"
    assert len(answer.citations) > 0

@patch("backend.retrieval.vector_search.embed_text", return_value=[0.1]*768)
async def test_reasoning_e2e_hybrid_unstable(mock_embed, setup_e2e_data):
    workspace_id = setup_e2e_data
    answer = await pipeline.query("Why was auth-service unstable last week?", workspace_id)
    assert answer.retrieval_strategy == "HYBRID"
    assert len(answer.citations) > 0
