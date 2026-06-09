# Retrieval & Reasoning Implementation Audit

## PRIMARY AUDIT OBJECTIVE
*   **Vector Retrieval:** Implemented, but **NOT WIRED**.
*   **Graph Retrieval:** Implemented, but **NOT WIRED**.
*   **Hybrid Retrieval:** Implemented, but **NOT WIRED**.
*   **Reasoning Pipeline:** Implemented, but **INJECTS MOCKED RETRIEVAL DATA**.

---

## PART 1 - VECTOR RETRIEVAL AUDIT
*   **File:** `backend/retrieval/vector_search.py`
*   **Function:** `vector_search()`
*   **Called By:** Unused. (Not called anywhere in the active codebase).
*   **Calls:** `embed_text`, `vector_repo.search_similar`, `select(EventModel)`
*   **Live or Mocked:** Live (contains actual `pgvector` execution logic).
*   **Unit Tests:** 0%
*   **Integration Tests:** 0%

**Answers:**
*   Does it query real pgvector tables? **Yes.**
*   Does it return real RetrievedChunk objects? **Yes.**
*   Is it used anywhere by the reasoning pipeline? **No.**

---

## PART 2 - GRAPH RETRIEVAL AUDIT
*   **File:** `backend/retrieval/graph_search.py`
*   **Function:** `graph_search()`
*   **Called By:** Unused.
*   **Calls:** `_extract_query_entities`, `graph_queries.find_events_by_entity`, PostgreSQL `EventModel` hydration.
*   **Live or Mocked:** Live (executes Neo4j traversals via AsyncDriver).
*   **Unit Tests:** 0%
*   **Integration Tests:** 0%

**Answers:**
*   Does it query real Neo4j? **Yes.**
*   Does it return real RetrievedChunk objects? **Yes.**
*   Is it used anywhere by the reasoning pipeline? **No.**

---

## PART 3 - HYBRID RETRIEVAL AUDIT
*   **File:** `backend/retrieval/hybrid.py`
*   **Function:** `merge()`
*   **Called By:** Unused.
*   **Calls:** Only `RetrievedChunk` schema mapping.
*   **Live or Mocked:** Pure python logic.
*   **Unit Tests:** 100%
*   **Integration Tests:** 0%

**Answers:**
*   Is hybrid retrieval actually invoked? **No.** It is implemented as a pure function but remains completely unused by the orchestrator.

---

## PART 4 - REASONING PIPELINE AUDIT

*   **Classifier:** `backend/reasoning/classifier.py` (`classifier.classify()`)
    *   **Called By:** `pipeline.py`
    *   **Calls:** Deterministic RegEx / List evaluation.
    *   **Live/Mocked:** Live.
*   **Planner:** `backend/reasoning/planner.py` (`planner.plan()`)
    *   **Called By:** `pipeline.py`
    *   **Calls:** Static mapping.
    *   **Live/Mocked:** Live.
*   **Pipeline:** `backend/reasoning/pipeline.py` (`ReasoningPipeline.query()`)
    *   **Called By:** `backend/api/v1/reasoning.py`
    *   **Calls:** `config_repo`, `classifier`, `planner`, `composer`, `citation_validator`.
    *   **Live/Mocked:** **MOCKED.** It intercepts the retrieval step and injects a hardcoded dictionary.
*   **Composer:** `backend/reasoning/composer.py` (`composer.synthesize()`)
    *   **Called By:** `pipeline.py`
    *   **Calls:** `tiktoken`, `llm_client.generate_completion()`
    *   **Live/Mocked:** Live execution, but operates on the mocked chunks passed from the pipeline.
*   **Citation Validator:** `backend/reasoning/citation.py` (`citation_validator.validate()`)
    *   **Called By:** `pipeline.py`
    *   **Calls:** RegEx validation against retrieved chunks.
    *   **Live/Mocked:** Live execution, operates on mocked chunks.
*   **LLM Client:** `backend/reasoning/llm_client.py` (`LLMClient.generate_completion()`)
    *   **Called By:** `composer.py`
    *   **Calls:** `google.generativeai`, `openai`, or `anthropic` network requests.
    *   **Live/Mocked:** Live.

---

## PART 5 - REAL QUERY TRACE
**Query:** "Who owns auth-service and what recent events affected it?"

**Exact Runtime Path:**
1.  **API Endpoint:** `POST /api/v1/reasoning/query` (`backend/api/v1/reasoning.py` Line 21)
2.  **Function:** `pipeline.query()` (`backend/reasoning/pipeline.py` Line 20)
3.  **Database Query:** `config_repo.get_known_entities()` (`backend/reasoning/pipeline.py` Line 35) -> *Queries PostgreSQL*
4.  **Function:** `classifier.classify()` (`backend/reasoning/classifier.py` Line 25)
5.  **Function:** `planner.plan()` (`backend/reasoning/planner.py` Line 13)
6.  **Retrieval Result:** **[MOCKED BYPASS]** `mock_retrieved_chunks` array is hardcoded at `backend/reasoning/pipeline.py` Line 44. **No vector or graph search is performed.**
7.  **Function:** `composer.synthesize()` (`backend/reasoning/composer.py` Line 26) -> *Uses tiktoken*
8.  **LLM Call:** `llm_client.generate_completion()` (`backend/reasoning/llm_client.py` Line 26) -> *Network Request*
9.  **Function:** `citation_validator.validate()` (`backend/reasoning/citation.py` Line 16)
10. **Return:** `GroundedAnswer` schema generated (`backend/reasoning/pipeline.py` Line 56).

---

## PART 6 - MOCK DETECTION

**Instance 1: Pipeline Shell Mock**
*   **File:** `backend/reasoning/pipeline.py`
*   **Function:** `ReasoningPipeline.query` (Lines 43-46)
*   **Why it exists:** "Mocked payload for shell." Used by developers to test the classifier/composer/LLM flow without running local Neo4j/PgVector instances.
*   **Severity:** **CRITICAL BLOCKER.** The system cannot answer real questions about ingested data.
*   **Fix effort estimate:** 1 hour. Requires importing `vector_search`, `graph_search`, and `hybrid.merge`, awaiting them, and passing the `RetrievedChunk` objects to the composer.

**Instance 2: LLM Client Mock**
*   **File:** `backend/reasoning/llm_client.py`
*   **Function:** `generate_completion` (Line 30)
*   **Why it exists:** Test utility. Used when `.env` sets `LLM_PROVIDER=mock` to avoid API billing during unit tests.
*   **Severity:** None. This is standard configuration-based test injection.

---

## PART 7 - FEATURE COMPLETION MATRIX

| Feature | Implemented | Wired Live | Tested E2E | Production Ready |
| :--- | :--- | :--- | :--- | :--- |
| Vector Retrieval | YES | NO | NO | NO |
| Graph Retrieval | YES | NO | NO | NO |
| Hybrid Retrieval | YES | NO | NO | NO |
| Reasoning Pipeline | YES | PARTIAL (Mocked) | NO | NO |
| Citation Validation | YES | YES | NO | NO |
| Config Registry | YES | YES | NO | YES |
| Config Sync | YES | YES | NO | YES |
| Reasoning API | YES | PARTIAL | NO | NO |
| Explain API | YES | PARTIAL | NO | NO |

---

## PART 8 - COVERAGE AUDIT
*Actual coverage measured via `pytest --cov` on 2026-06-09:*

| Module | Unit Coverage | Integration Coverage | E2E Coverage |
| :--- | :--- | :--- | :--- |
| Vector Retrieval | 0% | 0% | 0% |
| Graph Retrieval | 0% | 0% | 0% |
| Hybrid Retrieval | 100% | 0% | 0% |
| Pipeline | 0% | 100% | 0% |
| Composer | 0% | 96% | 0% |
| Classifier | 0% | 86% | 0% |

*(Note: Pipeline Integration coverage is artificially 100% because the mocked chunk allows the test to pass without hitting the unwritten/untested retrieval glue).*

---

## PART 9 - PHASE COMPLETION AUDIT

| Workstream | Status |
| :--- | :--- |
| Architecture | COMPLETE |
| Models | COMPLETE |
| Database | COMPLETE |
| Ingestion | COMPLETE |
| Memory Construction | COMPLETE |
| Vector Retrieval | PARTIAL |
| Graph Retrieval | PARTIAL |
| Hybrid Retrieval | PARTIAL |
| Reasoning Engine | PARTIAL |
| Config Registry | COMPLETE |
| API Layer | PARTIAL |
| Frontend | MISSING |
| Evaluation | MISSING |
| Observability | MISSING |
| Timeline Intelligence | DEFERRED |
| Decision Intelligence | DEFERRED |

**Calculations:**
*   Backend Completion: ~90%
*   MVP Completion: 60%
*   Production Readiness: 0%
*   Overall Product Completion: 50%

---

## PART 10 - FINAL VERDICT

**B) Phase 5 COMPLETE WITH INTEGRATION GAPS**

The reasoning and retrieval components have all been written, but they were never wired together. The pipeline is faking retrieval to simulate a successful run.

**Exact Remaining Work:**
1.  **Modify `backend/reasoning/pipeline.py`:** Remove the `mock_retrieved_chunks` array. Inject `AsyncSession` and `Neo4j AsyncDriver` into the pipeline. Call `vector_search` and `graph_search` concurrently based on the `RetrievalPlan`, then pass the outputs through `hybrid.merge`.
2.  **Modify Tests:** Create unit tests for `vector_search.py` and `graph_search.py`. Update `test_pipeline.py` so it mocks the dependencies (`vector_search`, `graph_search`) rather than hardcoding the logic inside the application code.

**Estimates:**
*   **Files requiring modification:** 3-4 files.
*   **Expected Effort:** 3-5 Hours.
*   **Phase Ownership:** This is strictly **Phase 5** technical debt. Do not proceed to Phase 6 API Polish until the reasoning layer actually queries the database.
