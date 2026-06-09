# Purpose:      Hybrid retrieval — merges vector and graph results, deduplicates
#               by event_id, applies combined scoring, and returns top-K chunks.
#               This is a pure function — no DB access, no external calls.
#               All inputs are pre-computed lists of RetrievedChunks.
# Called By:    Any caller that wants hybrid retrieval results.
#               In Phase 5+: retrieval orchestrator / query planner.
# Calls:        retrieval/schemas.py (RetrievedChunk)
# Dependencies: python stdlib only
# Test File:    tests/unit/retrieval/test_hybrid.py

from backend.retrieval.schemas import RetrievedChunk

# Weighting constants for combined score.
# 70% weight on semantic similarity, 30% on graph traversal signal.
VECTOR_WEIGHT = 0.7
GRAPH_WEIGHT = 0.3


def _compute_combined_score(vector_score: float, graph_score: float) -> float:
    """Compute weighted combined score. Clamped to [0.0, 1.0]."""
    raw = (VECTOR_WEIGHT * vector_score) + (GRAPH_WEIGHT * graph_score)
    return round(min(1.0, max(0.0, raw)), 4)


def merge(
    vector_results: list[RetrievedChunk],
    graph_results: list[RetrievedChunk],
    k: int = 10,
) -> list[RetrievedChunk]:
    """
    Merge vector and graph retrieval results into a single ranked list.

    Strategy:
      1. Index all chunks by event_id.
      2. For event_ids appearing in both lists, combine their scores.
      3. For event_ids appearing in one list only, use that list's score.
      4. Recompute combined_score for all chunks.
      5. Sort descending by combined_score.
      6. Return top-K.

    This function is a pure function — no side effects, no I/O.
    Easy to test with fixed inputs.

    Args:
        vector_results: Chunks from vector_search.py (vector_score set).
        graph_results:  Chunks from graph_search.py (graph_score set).
        k:              Maximum number of results to return.

    Returns:
        Deduplicated, ranked list of RetrievedChunks, at most k items.
    """
    # Build a mutable dict keyed by event_id
    merged: dict[str, dict] = {}

    for chunk in vector_results:
        key = str(chunk.event_id)
        merged[key] = {
            "chunk": chunk,
            "vector_score": chunk.vector_score,
            "graph_score": 0.0,
        }

    for chunk in graph_results:
        key = str(chunk.event_id)
        if key in merged:
            # Event appeared in both — take max vector_score, set graph_score=1.0
            merged[key]["graph_score"] = 1.0
        else:
            merged[key] = {
                "chunk": chunk,
                "vector_score": 0.0,
                "graph_score": chunk.graph_score,
            }

    # Rebuild RetrievedChunks with final combined score
    final: list[RetrievedChunk] = []
    for entry in merged.values():
        chunk: RetrievedChunk = entry["chunk"]
        v = entry["vector_score"]
        g = entry["graph_score"]
        combined = _compute_combined_score(v, g)
        final.append(
            chunk.model_copy(
                update={
                    "vector_score": round(v, 4),
                    "graph_score": round(g, 4),
                    "combined_score": combined,
                }
            )
        )

    # Sort descending by combined_score, then by timestamp as tiebreaker
    final.sort(key=lambda c: (c.combined_score, c.timestamp), reverse=True)

    return final[:k]
