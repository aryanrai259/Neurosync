# Traceability Matrix

**Last updated:** 2026-07-16 (end of day) — 3 bugs found via live verification earlier the same day, all fixed and re-verified live. See `docs/current/CURRENT_STATE.md` §1.

| Planned Capability | Planned Location | Actual Implementation | Status | ADR |
| :--- | :--- | :--- | :--- | :--- |
| **Ingestion Pipeline (raw persistence)** | `backend/ingestion/` | `backend/ingestion/worker.py` | ✅ COMPLETE | — |
| **Ingestion → Memory/Vector/Graph wiring** | `backend/api/v1/ingest.py` | `_build_worker()` now wires `memory_constructor`/`vector_indexer`/`graph_writer` | ✅ **FIXED — confirmed live 2026-07-16** | — |
| **Slack Adapter** | `backend/ingestion/adapters/` | `backend/ingestion/adapters/synthetic.py` (simulated) | ⚠️ PARTIAL | — |
| **GitHub Adapter** | `backend/ingestion/adapters/` | `backend/ingestion/adapters/github.py` | ✅ COMPLETE | — |
| **Jira Adapter** | `backend/ingestion/adapters/` | `backend/ingestion/normalizers/jira.py` (normalizer only, no live adapter) | ⚠️ PARTIAL | — |
| **Entity Resolution** | `backend/memory/entity_resolver.py` | `backend/memory/entity_resolver.py` (3-tier deterministic) | ✅ COMPLETE | — |
| **Relationship Extraction** | `backend/memory/relationship_extractor.py` | `backend/memory/relationship_extractor.py` (5 rules active) | ⚠️ PARTIAL (OWNS/RELATED_TO disabled) | — |
| **Memory Construction** | `backend/memory/` | `backend/memory/memory_constructor.py` | ✅ COMPLETE, confirmed live via the ingestion API | — |
| **Vector Database** | Pinecone / Milvus | PostgreSQL + `pgvector` | ✅ COMPLETE | ADR-0001 |
| **Vector Retrieval** | `backend/retrieval/vector_search.py` | `backend/retrieval/vector_search.py` | ✅ COMPLETE, confirmed live end-to-end | ADR-0001 |
| **Graph Database** | Neo4j | Neo4j | ✅ COMPLETE | — |
| **Graph Retrieval** | `backend/retrieval/graph_search.py` | `backend/retrieval/graph_search.py` | ✅ COMPLETE, confirmed live end-to-end | — |
| **Hybrid Retrieval** | `backend/retrieval/hybrid.py` | `backend/retrieval/hybrid.py` + wired in `pipeline.py` | ✅ COMPLETE, confirmed live end-to-end | — |
| **BM25 / Keyword Retrieval** | `backend/retrieval/keyword_search.py` | N/A | ❌ NOT STARTED | — |
| **Cross-encoder Reranker** | `backend/retrieval/reranker.py` | N/A | ❌ NOT STARTED | — |
| **LLM Orchestration** | `backend/reasoning/orchestrator.py` | `backend/reasoning/pipeline.py` | ✅ COMPLETE, confirmed live with real LLM key | ADR-0001 |
| **Query Classification** | `backend/reasoning/query.py` (LLM-based) | `backend/reasoning/classifier.py` (Deterministic) | ✅ COMPLETE, confirmed live | ADR-0001 |
| **Retrieval Planner** | `backend/reasoning/planner.py` | `backend/reasoning/planner.py` | ✅ COMPLETE | — |
| **Answer Composer** | `backend/reasoning/composer.py` | `backend/reasoning/composer.py` | ✅ COMPLETE, confirmed live | — |
| **Citation Validator** | `backend/reasoning/citation.py` | `backend/reasoning/citation.py` | ✅ COMPLETE, confirmed live (real citation returned for a real query) | — |
| **LLM Provider Abstraction** | `backend/reasoning/llm_client.py` | `backend/reasoning/llm_client.py` (Gemini, OpenAI, Anthropic, Groq, mock) | ✅ COMPLETE | — |
| **Retrieval Observability Trace** | — | `backend/reasoning/schemas.py` (RetrievalTrace) + logged in pipeline | ⚠️ PARTIAL (logged only, not stored) | — |
| **Config Registry** | N/A | `backend/db/repositories/config_repo.py` + `backend/config/service.py` | ✅ COMPLETE | ADR-0001 |
| **Decision Module** | `backend/reasoning/decision_module.py` | `backend/reasoning/decision_module.py` + `decisions` table + API | ✅ COMPLETE, confirmed live — real decision auto-extracted from ingested text | — |
| **Timeline Module** | `backend/reasoning/timeline_module.py` | `backend/reasoning/timeline_module.py` + API | ✅ **FIXED — confirmed live 2026-07-16**, correctly bucketed events returned | — |
| **Dependency Module** | `backend/reasoning/dependency_module.py` | N/A | ❌ NOT STARTED | — |
| **Decisions Table** | `decisions` in PostgreSQL | `backend/db/models/decision.py` + migration | ✅ COMPLETE | — |
| **API Layer** | `backend/api/v1/` | 12 routers: `reasoning`, `ingest`, `config`, `workspaces`, `auth`, `jobs`, `health`, `metrics`, `admin`, `decisions`, `timeline` | ✅ COMPLETE, all confirmed working live | — |
| **Authentication** | `backend/core/auth.py` | `backend/core/auth.py` + `api_keys` table | ✅ COMPLETE, confirmed live | — |
| **Rate Limiting** | API middleware | `backend/core/rate_limiter.py` | ✅ Built, unit-tested; not load-tested live | — |
| **CORS** | `backend/main.py` | Present per Phase 6A scope | ⚠️ Not explicitly re-verified live | — |
| **Admin Endpoints** | `backend/api/v1/admin.py` | `reset` (untested, not exercised), `reindex` (✅ **fixed**, confirmed live) | ✅ `reindex` confirmed working + tested; `reset` still untested | — |
| **Timeline API** | `GET /api/v1/timeline/{entity_id}` | `backend/api/v1/timeline.py` | ✅ **FIXED — confirmed live 2026-07-16** | — |
| **Observability / Telemetry** | `backend/core/telemetry.py` | `backend/core/telemetry.py` + `/api/v1/metrics*` | ✅ COMPLETE, confirmed live | — |
| **Evaluation Framework** | `scripts/evaluate.py` | `scripts/evaluate.py` + `data/eval/golden_queries.json` (10 queries) | ✅ Harness works correctly; post-fix run shows 3 genuine `HIGH`-confidence citations (up from 0/10) | — |
| **Next.js Frontend** | `frontend/` | `.gitkeep` placeholders only | ❌ NOT STARTED | — |

**How to read this table:** "✅ COMPLETE" means confirmed working in a live session, not just "code exists and unit tests pass" — the previous version of this document conflated the two, which is exactly how the three 2026-07-16 bugs shipped unnoticed.
