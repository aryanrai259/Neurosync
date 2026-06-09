# Purpose:      Data models for the Reasoning Layer.
# Called By:    classifier.py, planner.py, composer.py
# Dependencies: pydantic

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class QueryIntent(BaseModel):
    """Output of the deterministic classifier."""
    strategy: Literal["VECTOR_ONLY", "GRAPH_ONLY", "HYBRID", "UNKNOWN"]
    extracted_entities: list[str] = Field(default_factory=list)
    is_clarification_needed: bool = False


class RetrievalPlan(BaseModel):
    """Output of the planner."""
    strategy: Literal["VECTOR_ONLY", "GRAPH_ONLY", "HYBRID"]
    max_vector_results: int
    max_graph_results: int
    max_context_tokens: int


class RetrievalTrace(BaseModel):
    """Observability trace for retrieval execution."""
    strategy: str
    vector_results_count: int
    graph_results_count: int
    merged_results_count: int
    retrieval_ms: int
    vector_ms: int
    graph_ms: int



class GroundedAnswer(BaseModel):
    """Final output schema of the reasoning pipeline."""
    query_id: UUID
    answer_markdown: str
    retrieval_strategy: Literal["VECTOR_ONLY", "GRAPH_ONLY", "HYBRID"]
    citations: list[UUID]
    confidence: Literal["HIGH", "MEDIUM", "LOW"]
    execution_ms: int
