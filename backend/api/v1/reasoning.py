# Purpose:      REST API endpoints for the Reasoning Layer.
# Called By:    FastAPI router.
# Dependencies: fastapi, reasoning.pipeline

from uuid import UUID

from fastapi import APIRouter, Request
from pydantic import BaseModel

from backend.core.rate_limiter import limiter, QUERY_RATE
from backend.reasoning.pipeline import pipeline
from backend.reasoning.schemas import GroundedAnswer

router = APIRouter(prefix="/api/v1/reasoning", tags=["reasoning"])


class QueryRequest(BaseModel):
    workspace_id: UUID
    query: str


@router.post("/query", response_model=GroundedAnswer)
@limiter.limit(QUERY_RATE)
async def query_reasoning(request: Request, body: QueryRequest):
    """
    Standard query endpoint. Returns the final answer and citations.
    Rate limited: 20 requests/minute per API key or IP.
    """
    answer = await pipeline.query(body.query, body.workspace_id)
    return answer


@router.post("/explain")
@limiter.limit(QUERY_RATE)
async def explain_query(request: Request, body: QueryRequest):
    """
    MVP: Explains the execution plan without returning a full answer.
    Rate limited: 20 requests/minute per API key or IP.
    """
    answer = await pipeline.query(body.query, body.workspace_id)

    return {
        "query_id": answer.query_id,
        "strategy": answer.retrieval_strategy,
        "execution_ms": answer.execution_ms,
        "citations": answer.citations,
        "confidence": answer.confidence,
    }
