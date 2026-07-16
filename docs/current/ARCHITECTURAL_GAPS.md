# Architectural Gap Analysis

**Last updated:** 2026-07-16 (end of day) — a live verification pass earlier the same day found 3 bugs; all have since been fixed and re-verified live. See `docs/current/CURRENT_STATE.md` §1 for the full incident writeup. This document is kept as a record of the gap category, since the underlying lesson (integration seams need integration tests, not just component tests) outlives the specific fix.

## Critical: Untested Integration Seam — ROOT CAUSE, NOW ADDRESSED

The codebase had a structural blind spot: **every component was tested in isolation with hand-seeded data, but nothing tested the seam where `IngestionWorker` hands off to `MemoryConstructor` → `VectorIndexer` → `GraphWriter`.** Concretely, before the fix:
- `backend/api/v1/ingest.py::_build_worker()` (production) and `tests/integration/ingestion/test_worker.py::worker()` fixture (the "integration" test) both constructed `IngestionWorker` without `memory_constructor`/`vector_indexer`/`graph_writer`.
- `tests/e2e/reasoning/test_reasoning_e2e.py` — the file whose name implies it proves the system works end-to-end — never called the ingestion API or worker at all; it inserted `EventModel` and `EventEmbeddingModel` rows directly via SQLAlchemy and mocked the LLM provider.
- Net effect: the test suite was 100% green (667/667) while the actual product loop (ingest → retrieve → cite) was completely non-functional through the real API.

**Fixed 2026-07-16:** `_build_worker()` now wires all three dependencies, and three new regression tests close the seam: `TestSyntheticIngestionPopulatesRetrieval` (in `test_ingest_api.py`), `tests/integration/api/test_admin.py`, `tests/integration/api/test_timeline_api.py`. Suite is now 676/676 passing, 87% coverage. **The lesson to keep, even though the bug is fixed:** "integration coverage," not just unit/component coverage, is required wherever a background worker hands data to multiple independent subsystems — watch for this pattern recurring elsewhere in the codebase (e.g. if a new downstream consumer is added to the pipeline later).

## Bugs Found and Fixed (2026-07-16, same day)

1. **Ingestion didn't embed or graph-write.** `POST /api/v1/ingest/{synthetic,github}` left `events.embedding_status = PENDING` forever; `event_embeddings` never got a row; Neo4j never got a node. **Fixed** — see above. **Verified live:** fresh workspace, real ingestion, `embedding_status` → `EMBEDDED`, real cited `HIGH`-confidence reasoning answer.
2. **`POST /api/v1/admin/reindex/{id}` crashed.** `VectorIndexer.__init__() got an unexpected keyword argument 'vector_repo'` — wrong kwarg name (real param is `repo`), and the caller invoked a nonexistent `index_event()` method (real method is `index()`). **Fixed** — corrected kwarg/method, and now constructs a minimal `MemoryObject` from the `EventModel` row (vector-only re-embed, matching the endpoint's documented scope). **Verified live:** reindexed the original broken workspace, both events went `PENDING` → `EMBEDDED`.
3. **`GET /api/v1/timeline/{ws}/entity/{id}` 500'd always.** `backend/db/repositories/timeline_repo.py` referenced `EventModel.event_timestamp` and `EventModel.raw_content`, neither of which exist (real columns: `timestamp`, `content`). **Fixed** — all wrong attribute references corrected. **Verified live:** endpoint now returns `200` with correctly bucketed events.
4. **`backend/api/v1/admin.py` had zero test coverage.** Its own header comment referenced `tests/integration/api/test_admin.py`, which didn't exist. **Fixed** — the file now exists and covers `reindex` (202 + queued count, 404 for unknown workspace, 401 without API key, and the embedding-status side effect).

## Missing Modules
- **Dependency Module:** Mentioned in the traceability matrix as planned (`reasoning/dependency_module.py`) — still not started. Lower priority than the bugs above.

## Missing APIs
- **Entity Resolution / Manual CRUD:** No endpoints exist to manually edit aliases or merge duplicate entities outside the configuration registry. Still true as of 2026-07-16.
- **Deep health check** (`GET /api/v1/health/deep` checking DB + Neo4j connectivity) — referenced in the roadmap as a Phase 6A deliverable; not confirmed present in this pass.

## Missing UI Components
- **Entire Frontend:** `frontend/` contains only `.gitkeep` placeholders (`src/components`, `src/pages`, `src/hooks`, `public`). No Next.js scaffold exists. (`README.md` previously said "In Progress" — that was inaccurate; see doc-drift fixes.)

## Missing Tests — CLOSED 2026-07-16
- ~~The integration seam described above~~ — now covered by `TestSyntheticIngestionPopulatesRetrieval`.
- ~~`backend/api/v1/admin.py` zero coverage~~ — now covered by `tests/integration/api/test_admin.py`.
- ~~No test drives `POST /ingest/synthetic` → `POST /reasoning/query` → asserts a citation~~ — `test_reasoning_e2e.py` and `test_pipeline.py` still bypass ingestion by design (they're testing the reasoning layer in isolation, which is a legitimate thing to test), but the new `test_ingest_api.py` tests now cover the real end-to-end flow this gap described.

## Abandoned Ideas
- **LLM Intent Routing:** The idea of using an LLM to route queries (`QueryRouter`) was abandoned for speed and cost in favor of the deterministic classifier. (Unchanged — this was a good call, confirmed by the classifier working correctly in live testing.)

## Accidental Complexity
- **Two Build Guides:** `Build_Manual.md` and `Implementation_Plan.md` still both exist and can cause confusion.
- **`docs/MANUAL_BACKEND_GUIDE.md` has stale connection details:** its example `.env` block uses `DATABASE_URL=postgresql+asyncpg://neuro:neuro_pass@localhost:5432/neuro`, but the actual `docker-compose.yml` maps Postgres to host port **5433** with different credentials (`neuro_user`/`neuro_password`/`neuro_db`), which is what the real `.env` correctly uses. The guide would send a new developer down a dead end. Also missing the required `--workspace-id` flag in its `scripts/evaluate.py` example.
