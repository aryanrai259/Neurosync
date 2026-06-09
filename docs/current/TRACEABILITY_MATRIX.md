# Traceability Matrix

**Last updated:** 2026-06-09 (Phase 5 closure)

| Planned Capability | Planned Location | Actual Implementation | Status | ADR |
| :--- | :--- | :--- | :--- | :--- |
| **Ingestion Pipeline** | `backend/ingestion/` | `backend/ingestion/worker.py` | ✅ COMPLETE | — |
| **Slack Adapter** | `backend/ingestion/adapters/` | `backend/ingestion/adapters/synthetic.py` (simulated) | ⚠️ PARTIAL | — |
| **GitHub Adapter** | `backend/ingestion/adapters/` | `backend/ingestion/adapters/github.py` | ✅ COMPLETE | — |
| **Jira Adapter** | `backend/ingestion/adapters/` | `backend/ingestion/normalizers/jira.py` (normalizer only, no live adapter) | ⚠️ PARTIAL | — |
| **Entity Resolution** | `backend/memory/entity_resolver.py` | `backend/memory/entity_resolver.py` (3-tier deterministic) | ✅ COMPLETE | — |
| **Relationship Extraction** | `backend/memory/relationship_extractor.py` | `backend/memory/relationship_extractor.py` (5 rules active) | ⚠️ PARTIAL (OWNS/RELATED_TO disabled) | — |
| **Memory Construction** | `backend/memory/` | `backend/memory/memory_constructor.py` | ✅ COMPLETE | — |
| **Vector Database** | Pinecone / Milvus | PostgreSQL + `pgvector` | ✅ COMPLETE | ADR-0001 |
| **Vector Retrieval** | `backend/retrieval/vector_search.py` | `backend/retrieval/vector_search.py` | ✅ COMPLETE (E2E proven) | ADR-0001 |
| **Graph Database** | Neo4j | Neo4j | ✅ COMPLETE | — |
| **Graph Retrieval** | `backend/retrieval/graph_search.py` | `backend/retrieval/graph_search.py` | ✅ COMPLETE (E2E proven) | — |
| **Hybrid Retrieval** | `backend/retrieval/hybrid.py` | `backend/retrieval/hybrid.py` + wired in `pipeline.py` | ✅ COMPLETE (E2E proven) | — |
| **BM25 / Keyword Retrieval** | `backend/retrieval/keyword_search.py` | N/A | ❌ NOT STARTED | — |
| **Cross-encoder Reranker** | `backend/retrieval/reranker.py` | N/A | ❌ NOT STARTED | — |
| **LLM Orchestration** | `backend/reasoning/orchestrator.py` | `backend/reasoning/pipeline.py` | ✅ COMPLETE | ADR-0001 |
| **Query Classification** | `backend/reasoning/query.py` (LLM-based) | `backend/reasoning/classifier.py` (Deterministic) | ✅ COMPLETE | ADR-0001 |
| **Retrieval Planner** | `backend/reasoning/planner.py` | `backend/reasoning/planner.py` | ✅ COMPLETE | — |
| **Answer Composer** | `backend/reasoning/composer.py` | `backend/reasoning/composer.py` | ✅ COMPLETE | — |
| **Citation Validator** | `backend/reasoning/citation.py` | `backend/reasoning/citation.py` | ✅ COMPLETE | — |
| **LLM Provider Abstraction** | `backend/reasoning/llm_client.py` | `backend/reasoning/llm_client.py` (Gemini, OpenAI, Anthropic, Groq, mock) | ✅ COMPLETE | — |
| **Retrieval Observability Trace** | — | `backend/reasoning/schemas.py` (RetrievalTrace) + logged in pipeline | ⚠️ PARTIAL (logged only, not stored) | — |
| **Config Registry** | N/A | `backend/db/repositories/config_repo.py` + `backend/config/service.py` | ✅ COMPLETE | ADR-0001 |
| **Decision Module** | `backend/reasoning/decision_module.py` | N/A | ❌ DEFERRED → Phase 6D | — |
| **Timeline Module** | `backend/reasoning/timeline_module.py` | N/A | ❌ DEFERRED → Phase 6E | — |
| **Dependency Module** | `backend/reasoning/dependency_module.py` | N/A | ❌ NOT STARTED | — |
| **Decisions Table** | `decisions` in PostgreSQL | N/A | ❌ NOT STARTED | — |
| **API Layer (basic)** | `backend/api/v1/` | `reasoning.py`, `ingest.py`, `config.py` | ⚠️ PARTIAL | — |
| **Authentication** | `backend/core/auth.py` | N/A | ❌ NOT STARTED → Phase 6B | — |
| **Rate Limiting** | API middleware | N/A | ❌ NOT STARTED → Phase 6C | — |
| **CORS** | `backend/main.py` | N/A | ❌ NOT STARTED → Phase 6A | — |
| **Admin Endpoints** | `backend/api/v1/admin.py` | N/A | ❌ NOT STARTED → Phase 6A | — |
| **Timeline API** | `GET /api/v1/timeline/{entity_id}` | N/A | ❌ NOT STARTED → Phase 6E | — |
| **Observability / Telemetry** | `backend/core/telemetry.py` | N/A | ❌ NOT STARTED → Phase 8A | — |
| **Evaluation Framework** | `scripts/evaluate.py` | `scripts/generate_retrieval_proof.py` (manual) | ⚠️ MANUAL ONLY | — |
| **Next.js Frontend** | `frontend/` | N/A | ❌ NOT STARTED → Phase 7 | — |
