# backend/retrieval

Phase 4D: Retrieval Foundation

## Purpose

Provides the retrieval layer that powers future reasoning (Phase 5+).
Takes a free-text query and returns ranked `RetrievedChunk` objects by combining
vector similarity search (PgVector) and graph traversal (Neo4j).

## Module Map

| File | Responsibility |
|------|----------------|
| `schemas.py` | `RetrievedChunk` — the canonical retrieval output type |
| `vector_search.py` | Embeds query, queries PgVector cosine similarity, hydrates EventModel |
| `graph_search.py` | Extracts query entities, traverses Neo4j, hydrates EventModel |
| `hybrid.py` | Pure merge function — deduplicates by event_id, combines scores, returns top-K |

## RetrievedChunk

```python
RetrievedChunk(
    event_id: UUID,        # FK -> events.id
    content: str,          # Event text (used for LLM context)
    source: SourceType,    # Where it came from
    timestamp: datetime,   # When it happened
    author_id: str,
    vector_score: float,   # 0.0-1.0 cosine similarity
    graph_score: float,    # 1.0 if from graph, 0.0 otherwise
    combined_score: float, # 0.7 * vector + 0.3 * graph
)
```

## Scoring

| Component | Weight | Signal |
|-----------|--------|--------|
| `vector_score` | 0.7 | Semantic similarity to query |
| `graph_score` | 0.3 | Graph-linked to query entities |
| `combined_score` | — | Weighted merge, used for final ranking |

## Retrieval Flow

```
Query string
    |
    +---> vector_search()          embed query -> cosine search -> hydrate
    |
    +---> graph_search()           extract entities -> Neo4j traverse -> hydrate
    |
    +---> hybrid.merge()           deduplicate by event_id -> rescore -> top-K
    |
    v
[RetrievedChunk, ...]
```

## Design Invariants

- `hybrid.merge()` is a pure function — no DB access, no I/O. Fully unit-testable.
- `vector_search()` returns empty list if Ollama is unavailable — does not raise.
- `graph_search()` returns empty list if Neo4j is unavailable — does not raise.
- Both search functions return the same `RetrievedChunk` type, making merge trivial.
- Deduplication by `event_id` ensures the same event never appears twice in results.
- Phase 5+ will add a retrieval orchestrator, caching, and query planning on top of this foundation.
