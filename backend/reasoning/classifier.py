# Purpose:      Deterministic Intent Classification MVP.
#               Uses regex and keyword matching instead of an LLM.
# Called By:    pipeline.py
# Dependencies: re

import re

from backend.reasoning.schemas import QueryIntent

# Structural intent keywords
GRAPH_KEYWORDS = {
    "who owns", "owned by", "depends on", "dependency", "dependencies",
    "repository", "repo for", "team for",
}

# Semantic/Hybrid intent keywords
HYBRID_KEYWORDS = {
    "recent", "error", "failing", "ticket", "issue", "PR", "commit", "why did", "what happened"
}


class DeterministicClassifier:
    """Classifies query intent purely via deterministic logic."""

    def classify(self, query: str, known_entities: set[str] = frozenset()) -> QueryIntent:
        """
        Classifies the query.
        known_entities: A set of known team names, service names, and repos from the DB.
        """
        query_lower = query.lower()

        # 1. Extract known entities
        extracted = []
        for entity in known_entities:
            if entity.lower() in query_lower:
                extracted.append(entity)

        # 2. Check for structural keywords
        has_graph_keyword = any(kw in query_lower for kw in GRAPH_KEYWORDS)
        
        # 3. Check for semantic keywords
        has_hybrid_keyword = any(kw in query_lower for kw in HYBRID_KEYWORDS)

        # 4. Routing Logic
        if not query.strip():
            return QueryIntent(strategy="UNKNOWN", is_clarification_needed=True)

        if has_graph_keyword and not has_hybrid_keyword and extracted:
            return QueryIntent(strategy="GRAPH_ONLY", extracted_entities=extracted)

        if extracted or has_hybrid_keyword:
            return QueryIntent(strategy="HYBRID", extracted_entities=extracted)

        return QueryIntent(strategy="VECTOR_ONLY")

classifier = DeterministicClassifier()
