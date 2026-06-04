# backend/retrieval

## Purpose
Fetches relevant context from storage in response to a planner query.
Implements three retrieval strategies: vector similarity, graph traversal,
and hybrid (both combined with reranking).

## Responsibilities
- Execute semantic vector search against ChromaDB/Qdrant
- Execute graph-based traversal against Neo4j
- Combine and rerank results from both sources
- Score and rank final candidates before returning to the reasoning layer

## Files (to be added)
| File | Responsibility |
|---|---|
| `vector_retriever.py` | Semantic search against vector store |
| `graph_retriever.py` | Graph traversal against Neo4j |
| `hybrid_retriever.py` | Combines vector + graph results |
| `reranker.py` | Cross-encoder reranking of candidates |
| `scorer.py` | Final scoring + confidence weighting |

## Dependency Arrow
```
reasoning/planner.py
  ↓
retrieval/ (this module)
  ├── vector_retriever.py → ChromaDB/Qdrant
  ├── graph_retriever.py  → Neo4j
  └── hybrid_retriever.py
        ↓
      reranker.py
        ↓
      scorer.py
        ↓
reasoning/composer.py
```

## Inputs
- `RetrievalQuery` object from `reasoning/planner.py`
  - Natural language query string
  - Filters (workspace, time range, source type, entities)
  - Strategy hint (vector / graph / hybrid)

## Outputs
- `List[RetrievedChunk]` — ranked list of context chunks with scores

## Dependencies
- `models/event.py`
- `models/entity.py`
- `core/database.py` (vector store + graph DB clients)
- `core/config.py`

## Future Extensions
- BM25 keyword retrieval (sparse + dense hybrid)
- Multi-hop graph traversal
- Temporal decay scoring
- Personalized ranking by user

## Example Flow
```
planner.py → RetrievalQuery(query="why did auth move to Redis?", strategy="hybrid")
  → hybrid_retriever.py
    → vector_retriever.py → top-20 vector results
    → graph_retriever.py  → related entities + events
  → reranker.py          → cross-encoder reranking → top-10
  → scorer.py            → final scores + confidence
  → List[RetrievedChunk] → composer.py
```
