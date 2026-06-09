# Purpose:      REST API endpoints for the Reasoning Layer.
# Called By:    FastAPI router.
# Dependencies: fastapi, reasoning.pipeline

from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel

from backend.reasoning.pipeline import pipeline
from backend.reasoning.schemas import GroundedAnswer

router = APIRouter(prefix="/api/v1/reasoning", tags=["reasoning"])


class QueryRequest(BaseModel):
    workspace_id: UUID
    query: str


@router.post("/query", response_model=GroundedAnswer)
async def query_reasoning(request: QueryRequest):
    """
    Standard query endpoint. Returns the final answer and citations.
    """
    answer = await pipeline.query(request.query, request.workspace_id)
    return answer


@router.post("/explain")
async def explain_query(request: QueryRequest):
    """
    MVP requirement: Explains the execution plan without returning a full answer.
    """
    # For MVP we can just run the query and return the answer,
    # or expose the classifier/planner trace directly.
    # We will reuse pipeline.query for now as it contains strategy and confidence.
    answer = await pipeline.query(request.query, request.workspace_id)
    
    return {
        "query_id": answer.query_id,
        "strategy": answer.retrieval_strategy,
        "execution_ms": answer.execution_ms,
        "citations": answer.citations,
        "confidence": answer.confidence,
    }
