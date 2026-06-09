# Purpose:      Retrieval Planner and Budgeting.
# Called By:    pipeline.py
# Dependencies: schemas.py

from backend.reasoning.schemas import QueryIntent, RetrievalPlan


class RetrievalPlanner:
    """
    Enforces strict retrieval budgets and routing.
    """

    MAX_VECTOR_RESULTS = 10
    MAX_GRAPH_RESULTS = 50
    MAX_CONTEXT_TOKENS = 6000

    def plan(self, intent: QueryIntent) -> RetrievalPlan:
        """Create a retrieval plan from the classified intent."""
        if intent.strategy == "VECTOR_ONLY":
            return RetrievalPlan(
                strategy="VECTOR_ONLY",
                max_vector_results=self.MAX_VECTOR_RESULTS,
                max_graph_results=0,
                max_context_tokens=self.MAX_CONTEXT_TOKENS,
            )
        elif intent.strategy == "GRAPH_ONLY":
            return RetrievalPlan(
                strategy="GRAPH_ONLY",
                max_vector_results=0,
                max_graph_results=self.MAX_GRAPH_RESULTS,
                max_context_tokens=self.MAX_CONTEXT_TOKENS,
            )
        else:
            return RetrievalPlan(
                strategy="HYBRID",
                max_vector_results=self.MAX_VECTOR_RESULTS,
                max_graph_results=self.MAX_GRAPH_RESULTS,
                max_context_tokens=self.MAX_CONTEXT_TOKENS,
            )

planner = RetrievalPlanner()
