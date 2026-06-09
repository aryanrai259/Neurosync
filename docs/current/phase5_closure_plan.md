# Phase 5 Closure Plan

## 1. Existing Retrieval Flow
The existing flow in `backend/reasoning/pipeline.py` intercepts retrieval after intent classification and planning. Instead of performing any vector or graph lookups, it hardcodes an array `mock_retrieved_chunks` and passes it directly to the LLM Composer. The actual retrieval functions (`vector_search` and `graph_search`) are completely disconnected and have zero unit or integration coverage.

## 2. Required Modifications
1. **Pipeline Restructuring (`backend/reasoning/pipeline.py`):**
   - Import `vector_search`, `graph_search`, and `hybrid`.
   - Remove `mock_retrieved_chunks`.
   - Instantiate Neo4j `AsyncDriver` (via `get_driver()`).
   - Use `asyncio.gather` to concurrently execute `vector_search` and `graph_search` based on the `RetrievalPlan.strategy`.
   - Pass the results into `hybrid.merge`.
   - Handle empty result scenarios gracefully (fail loudly if no context is found, avoiding hallucination).
2. **Remove Mocks:** Scan and remove any fake context generation references or remaining TODOs in the pipeline or tests (specifically `test_pipeline.py` which currently asserts on the mock).
3. **Add Tests:** Create `tests/unit/retrieval/test_vector_search.py`, `tests/unit/retrieval/test_graph_search.py`, and `tests/unit/retrieval/test_hybrid.py`. Add `tests/e2e/reasoning/test_reasoning_e2e.py`.

## 3. Dependency Injection Requirements
To execute live retrieval, `pipeline.py` must inject:
- `AsyncSession` (PostgreSQL connection for hydration, config_repo, and vector_repo)
- `AsyncDriver` (Neo4j connection for graph_queries)
- `vector_repo` (The singleton from `backend.db.repositories.vector_repo`)
- `workspace_id` (Already passed in from the API layer)

## 4. Testing Strategy
- **Unit Tests:** Mock the `AsyncSession` and `AsyncDriver` returns. Assert that `vector_search` accurately calls `embed_text` and `vector_repo.search_similar`, and `graph_search` accurately calls `find_events_by_entity`. Assert `hybrid.merge` logic dedupes correctly.
- **Integration Tests (`test_pipeline.py`):** Mock `vector_search` and `graph_search` inside the pipeline test so it doesn't need Neo4j/PgVector running, but DO NOT mock the chunk array inside application code.
- **E2E Tests:** Create a fixture to seed `events`, `event_embeddings`, `memory_objects`, and `graph nodes`. Call `pipeline.query()` with actual queries (e.g. "Who owns auth-service?") and assert real execution traces all the way to a grounded LLM answer.

## 5. Estimated Changes
- `backend/reasoning/pipeline.py` (+30 lines, -5 lines)
- `tests/integration/reasoning/test_pipeline.py` (+40 lines, -10 lines)
- `tests/unit/retrieval/test_vector_search.py` (+60 lines)
- `tests/unit/retrieval/test_graph_search.py` (+60 lines)
- `tests/unit/retrieval/test_hybrid.py` (+50 lines)
- `tests/e2e/reasoning/test_reasoning_e2e.py` (+150 lines)
