# System Current State

**Last updated:** 2026-07-16 (live verification pass, 3 bugs found and fixed same day, re-verified live)
**Stable phase:** Phase 0–6 + 8 — code-complete AND confirmed working end-to-end via the real HTTP API, live infra, and a real LLM.
**Not started:** Phase 7 (Frontend)

---

## 1. Executive Summary — READ THIS FIRST

Earlier on 2026-07-16, a live verification pass (full stack up: Docker Postgres+pgvector, Neo4j, Ollama with `nomic-embed-text`, a real LLM key) found three bugs that made the core product loop — **ingest data → ask a question → get a cited answer** — non-functional through the real HTTP API despite a fully green test suite. **All three have since been fixed, covered by new regression tests, and re-verified live the same day.** See §2 below for current-vs-original status; the bugs themselves are kept on record here because the gap between "tests pass" and "the product works" is exactly the kind of thing worth remembering.

**The three bugs (fixed):**
1. **Ingestion never populated the vector/graph indexes.** `backend/api/v1/ingest.py::_build_worker()` constructed `IngestionWorker` without `memory_constructor`, `vector_indexer`, or `graph_writer`. **Fix:** wired all three in `_build_worker()`. **Verified live:** ingested 2 events into a fresh workspace, `embedding_status` went to `EMBEDDED`, and `POST /reasoning/query` on the same content returned a real answer with a citation and `HIGH` confidence — where before it returned `"No supporting evidence found"`.
2. **`POST /api/v1/admin/reindex/{workspace_id}` crashed on every call** (`VectorIndexer.__init__() got an unexpected keyword argument 'vector_repo'`, plus a call to a nonexistent `index_event()` method). **Fix:** correct kwarg (`repo=`), correct method (`index()`), and construct a minimal `MemoryObject` from the `EventModel` row so vector-only re-embedding matches the endpoint's documented scope. **Verified live:** reindexed the original broken test workspace — both previously-`PENDING` events became `EMBEDDED`.
3. **`GET /api/v1/timeline/{workspace_id}/entity/{entity_id}` 500'd on every call** (`AttributeError: type object 'EventModel' has no attribute 'event_timestamp'`; also wrong `raw_content`/`raw_author` attribute names in the same file). **Fix:** corrected all three wrong attribute references in `backend/db/repositories/timeline_repo.py` to the real column names (`timestamp`, `content`, `author_id`). **Verified live:** the endpoint now returns `200` with correctly bucketed events.

**Why the original test suite didn't catch this — and what changed:** every `IngestionWorker` instantiation in the codebase previously omitted `memory_constructor`/`vector_indexer`/`graph_writer`, and no test exercised `admin.py` or `timeline_repo.py`'s entity-lookup path against the real endpoint. Three new regression tests now close exactly this gap:
- `tests/integration/ingestion/test_ingest_api.py::TestSyntheticIngestionPopulatesRetrieval` — drives `POST /ingest/synthetic` through the real endpoint and asserts `event_embeddings` and a Neo4j `Event` node actually get created.
- `tests/integration/api/test_admin.py` (new file) — drives `POST /admin/reindex` and asserts a `PENDING` event becomes `EMBEDDED`.
- `tests/integration/api/test_timeline_api.py` (new file) — drives `GET /timeline/.../entity/...` and asserts `200`, not `500`.

**Independent re-confirmation via the evaluation framework:** re-running `scripts/evaluate.py` against the (now-repaired) original test workspace returned 3 genuine `HIGH`-confidence answers with real citations (previously **zero** citations across all 10 queries, every answer literally `"No supporting evidence found"`). The remaining failures in that run were Gemini free-tier rate-limiting (`429`, 5 req/min quota) — an external API constraint, not a code defect.

**Test status:** 676 tests passing · 87% coverage · run live 2026-07-16, after the fixes (up from 667 tests / 86% before — the +9 are the new regression tests above).

---

## 2. Implemented Components

### Ingestion
- **Status:** ✅ Stable, confirmed live end-to-end (raw persistence, entity extraction, memory construction, embedding, graph write all fire on every ingested event). Fixed 2026-07-16 (§1, bug 1); regression-tested by `TestSyntheticIngestionPopulatesRetrieval`.
- **Key Files:** `backend/ingestion/worker.py`, `backend/api/v1/ingest.py`, `backend/ingestion/adapters/`, `backend/ingestion/normalizers/`

### Database
- **Status:** ✅ Stable
- **Key Files:** `backend/db/session.py`, `backend/db/models/`, `backend/db/repositories/`, `alembic/versions/`
- Migrations verified at head (`d7e8f9a0b1c2`) against a fresh container on 2026-07-16.

### Entity + Relationship Extraction
- **Status:** ✅ Stable (deterministic, no LLM) — flat entity registration confirmed live.
- **Key Files:** `backend/memory/entity_resolver.py`, `backend/memory/relationship_extractor.py`

### Vector Retrieval (pgvector)
- **Status:** ✅ Stable, confirmed live with real ingested data (was already component-proven; now also proven fed by real traffic).
- **Key Files:** `backend/retrieval/vector_search.py`, `backend/db/repositories/vector_repo.py`

### Graph Retrieval (Neo4j)
- **Status:** ✅ Stable, confirmed live — `Event` nodes are now written by the real ingestion path (verified: `MATCH (e:Event {event_id: ...})` returns a match immediately after a live `POST /ingest/synthetic` call).
- **Key Files:** `backend/retrieval/graph_search.py`, `backend/graph/queries.py`

### Hybrid Retrieval
- **Status:** ✅ Stable, confirmed live.
- **Key Files:** `backend/retrieval/hybrid.py`

### Reasoning Engine
- **Status:** ✅ Stable, confirmed live — a real query against freshly-ingested data now returns a grounded answer with a real citation and `HIGH` confidence (previously returned `"No supporting evidence found"` purely because nothing upstream fed it data; the component itself was always correct).
- **Key Files:** `backend/reasoning/pipeline.py`, `classifier.py`, `planner.py`, `composer.py`, `citation.py`, `llm_client.py`

### Config Registry
- **Status:** ✅ Stable

### API
- **Status:** ✅ Stable — all 12 routers confirmed working live, including the two that were previously broken.
- **Working:** `/health`, `/api/v1/workspaces`, `/api/v1/auth/keys`, `/api/v1/ingest/*`, `/api/v1/jobs/{id}`, `/api/v1/reasoning/query`, `/api/v1/reasoning/explain`, `/api/v1/config/*`, `/api/v1/metrics`, `/api/v1/metrics/health-summary`, `/api/v1/decisions/{workspace_id}`, `POST /api/v1/admin/reindex/{id}` (fixed), `GET /api/v1/timeline/{ws}/entity/{id}` (fixed)
- **Note:** `backend/api/v1/workspaces.py` still has an uncommitted local diff (409-on-duplicate-name handling) from before this session's fixes — not yet folded into a commit.
- `backend/api/v1/admin.py` now has test coverage (`tests/integration/api/test_admin.py`, new).

### Decision Intelligence
- **Status:** ✅ Stable, confirmed live — `extract_decision_candidates()` runs off retrieved chunks, which now populate correctly. Confirmed: ingesting "We decided to migrate the auth-service from Express to Go..." produced a real `Decision` row via `GET /api/v1/decisions/{workspace}` with correct title, description, and `source_event_id` provenance (previously returned `[]` for the same input).
- **Key Files:** `backend/reasoning/decision_module.py`, `backend/api/v1/decisions.py`, `backend/db/repositories/decision_repo.py`

### Timeline Intelligence
- **Status:** ✅ Stable, confirmed live — fixed 2026-07-16 (§1, bug 3); regression-tested by `tests/integration/api/test_timeline_api.py` (new).
- **Key Files:** `backend/reasoning/timeline_module.py`, `backend/api/v1/timeline.py`, `backend/db/repositories/timeline_repo.py`

### Authentication / Rate Limiting
- **Status:** ✅ Stable, confirmed live (401 without key, key issuance and header auth both work correctly).
- **Key Files:** `backend/core/auth.py`, `backend/core/rate_limiter.py`, `backend/api/middleware/auth.py`

### Observability
- **Status:** ✅ Stable, confirmed live (`/api/v1/metrics/health-summary` correctly tracked request/error counts during this session).
- **Key Files:** `backend/core/telemetry.py`, `backend/api/v1/metrics.py`

### Evaluation Framework
- **Status:** ✅ Runs correctly as a harness. Re-run after the fixes against the repaired original test workspace: 3 genuine `HIGH`-confidence citations returned (up from 0/10 before the fix). Remaining failures in that run were Gemini free-tier rate-limiting (`429`, external quota), not a code defect. `scripts/evaluate.py --workspace-id <id>` (the `--workspace-id` flag is required; `MANUAL_BACKEND_GUIDE.md` has been corrected to show it).
- **Key Files:** `scripts/evaluate.py`, `data/eval/golden_queries.json` (10 queries, not the 50 originally planned — see ROADMAP)

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

| Debt | Impact | Priority |
|------|--------|----------|
| Outdated core dependencies (`anthropic` 0.40→0.116 latest, `openai` 1.57→2.45, `fastapi` 0.115→0.139, `neo4j` driver 5.27→6.2) | No known breakage today; risk grows over time, esp. Anthropic SDK gap vs. current model IDs | 🟡 Medium |
| BM25/keyword retrieval missing | Fallback for no-embedding queries | 🟡 Backlog |
| FastAPI BackgroundTasks instead of Redis/Celery | No retry logic, no queue depth — the ingestion-wiring bug (fixed 2026-07-16) shipped silently for exactly this reason; a real queue with failure visibility would have surfaced it sooner | 🟡 Backlog |
| Golden eval set is 10 queries, not the 50 originally planned | Lower statistical confidence in eval scores | 🟡 Backlog |
| Eval run against a live LLM is rate-limited on Gemini free tier (5 req/min) | Full 10-query eval runs can't complete without hitting `429`s on a free-tier key | 🟡 Backlog — use a paid tier or add inter-query throttling to `evaluate.py` |
| Uncommitted local diff in `backend/api/v1/workspaces.py` (409-on-duplicate fix) | Not yet part of any commit | 🟡 Low — fold into next commit |

---

## 5. Production Readiness

**Backend is functionally complete and live-verified end-to-end as of 2026-07-16.** The ingest → embed → graph-write → retrieve → cite loop works through the real HTTP API with real infra and a real LLM. Remaining blockers before a genuine production deployment are the ones that were always known and never claimed otherwise:
- No load testing of rate limiting under real traffic
- Dependency versions are dated (see technical debt table)
- No frontend (Phase 7, not started)
- Eval set is small (10 queries) and hits free-tier LLM rate limits

---

## 6. Remaining Work (Ordered)

| Priority | Work |
|----------|------|
| 🟢 Done | ~~Fix `_build_worker()` ingestion wiring~~ — fixed and live-verified 2026-07-16 |
| 🟢 Done | ~~Fix `admin/reindex` crash~~ — fixed and live-verified 2026-07-16 |
| 🟢 Done | ~~Fix `timeline_repo.py` column names~~ — fixed and live-verified 2026-07-16 |
| 🟢 Done | ~~Add regression tests for the ingestion→memory/vector/graph seam~~ — added, 676/676 passing |
| 🟡 P1 | Fold the uncommitted `workspaces.py` diff into a commit |
| 🟡 P1 | Address dependency staleness (`anthropic`, `openai`, `fastapi`, `neo4j` driver) |
| 🟡 P2 | Expand golden eval set beyond 10 queries; add throttling or a paid-tier key so full runs don't hit `429`s |
| ⬜ P3 | Phase 7 — Frontend (now unblocked on the backend correctness front; still a from-scratch 3–4 week effort) |
