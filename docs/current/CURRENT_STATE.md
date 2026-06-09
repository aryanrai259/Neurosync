# System Current State

**Last updated:** 2026-06-09  
**Stable phase:** Phase 0–5 (E2E verified)  
**Active phase:** Phase 6 — API hardening, auth, admin tools, timeline + decision modules

---

## 1. Executive Summary

Company Brain is merged through Phase 5 on `dev`. The backend is operationally verified end-to-end: the full reasoning pipeline (Classify → Plan → Retrieve via pgvector + Neo4j → Hybrid Merge → LLM Synthesize → Cite) executes with real databases and real LLM responses.

**Proof:** `docs/current/retrieval_proof_report.md` — 5 live queries, real PostgreSQL + Neo4j + Gemini, all 5 traces validated with `HIGH` confidence citations.

**Test status:** 551 tests passing · 91% coverage

---

## 2. Implemented Components (Phase 0–5)

### Ingestion
- **Status:** ✅ Stable
- **Key Files:** `backend/ingestion/worker.py`, `backend/ingestion/adapters/`, `backend/ingestion/normalizers/`
- **Capabilities:** Synthetic ingestion, GitHub live ingestion, Slack/GitHub/Jira normalizers, checksum deduplication, entity extraction, relationship extraction, entity registry writes

### Database
- **Status:** ✅ Stable
- **Key Files:** `backend/db/session.py`, `backend/db/models/`, `backend/db/repositories/`, `alembic/versions/`
- **Tables:** workspaces, events, event_embeddings, memory_objects, ingestion_jobs, entity_registry, config_services, config_teams, config_repositories

### Entity + Relationship Extraction
- **Status:** ✅ Stable (deterministic, no LLM)
- **Key Files:** `backend/memory/entity_resolver.py`, `backend/memory/relationship_extractor.py`
- **Extracts:** PERSON, SERVICE, TEAM, TICKET, REPOSITORY, DECISION entities; AUTHORED, AFFECTS, DISCUSSED_IN, REFERENCES, DEPENDS_ON relationships

### Vector Retrieval (pgvector)
- **Status:** ✅ Stable — E2E proven
- **Key Files:** `backend/retrieval/vector_search.py`, `backend/db/repositories/vector_repo.py`
- **Embeddings:** Ollama `nomic-embed-text`, stored in `event_embeddings` with model name versioning

### Graph Retrieval (Neo4j)
- **Status:** ✅ Stable — E2E proven
- **Key Files:** `backend/retrieval/graph_search.py`, `backend/graph/queries.py`
- **Traversal:** AFFECTS, REFERENCES, AUTHORED edges; scoped by workspace_id

### Hybrid Retrieval
- **Status:** ✅ Stable — E2E proven (replaces prior mocked pipeline)
- **Key Files:** `backend/retrieval/hybrid.py`
- **Strategy:** Score fusion (vector_score × 0.7 + graph_score × 0.3), deduped by event_id

### Reasoning Engine
- **Status:** ✅ Stable — E2E proven
- **Key Files:** `backend/reasoning/pipeline.py`, `classifier.py`, `planner.py`, `composer.py`, `citation.py`, `llm_client.py`
- **Flow:** Query → Classify (deterministic) → Plan (token-budgeted) → Concurrent Vector+Graph → Merge → Synthesize (LLM) → Validate Citations → Return GroundedAnswer
- **LLM providers:** Gemini, OpenAI, Anthropic, Groq, mock

### Config Registry
- **Status:** ✅ Stable
- **Key Files:** `backend/config/service.py`, `backend/db/repositories/config_repo.py`
- **Capability:** Manages workspace services/teams/repos in PostgreSQL; syncs to Neo4j graph on demand

### API
- **Status:** ⚠️ Partial (Phase 6 foundation)
- **Key Files:** `backend/api/v1/reasoning.py`, `backend/api/v1/config.py`, `backend/api/v1/ingest.py`
- **Active endpoints:** `/api/v1/reasoning/query`, `/api/v1/ingest/synthetic`, `/api/v1/ingest/github`, `/api/v1/config/*`, `/health`
- **Missing:** Auth, CORS, rate limiting, admin endpoints, timeline/decision endpoints, workspace management, job status

---

## 3. Architectural Deviations from Original Spec

| Deviation | Details | ADR |
|-----------|---------|-----|
| `pgvector` instead of ChromaDB/Pinecone | pgvector integrated into existing PostgreSQL, eliminating separate vector store | ADR-0001 |
| Deterministic classifier instead of LLM QueryRouter | Keyword + entity matching replaces LLM routing (faster, cheaper, deterministic) | ADR-0001 |
| Graph topology anchored to Config Registry | Ownership known from registry, not inferred from unstructured events | ADR-0001 |
| Provider-agnostic LLM interface | `llm_client.py` supports Gemini, OpenAI, Anthropic, Groq | ADR-0001 |
| OWNS + RELATED_TO rules disabled | Prevents graph super-node growth; deferred to config-based ownership | Phase 4 decision |

---

## 4. Current Known Technical Debt

| Debt | Impact | Plan |
|------|--------|------|
| No authentication | Any request reaches pipeline | Phase 6B — API key auth |
| No CORS | Blocks frontend | Phase 6A — CORS middleware |
| No rate limiting | Vulnerable to abuse | Phase 6C — slowapi |
| No `decisions` table | Decision intelligence missing | Phase 6D |
| Timeline module deferred | MVP gap | Phase 6E |
| BM25/keyword retrieval missing | Fallback for no-embedding queries | Phase 6 backlog |
| No observability | No metrics, no query trace storage | Phase 8A |
| FastAPI BackgroundTasks instead of Redis/Celery | No retry logic, no queue depth | Phase 6 backlog |

---

## 5. Production Readiness

**NOT production-ready.** The backend is a functional, verified alpha. Blockers:
- No authentication or authorization
- No rate limiting
- Missing MVP features (Timeline, Decision modules)
- No observability infrastructure

---

## 6. Remaining Work (Ordered)

| Phase | Work | Priority |
|-------|------|----------|
| 6A | CORS + deep health + workspaces + jobs API | Critical |
| 6B | API key authentication | Critical |
| 6C | Rate limiting | Important |
| 6D | Decision intelligence | Important |
| 6E | Timeline intelligence | Important |
| 8A | Observability (Prometheus metrics, JSON logging) | Important |
| 8B | Evaluation framework (50-query golden set) | Nice-to-have |
| 7 | Frontend (Next.js) | After backend complete |
