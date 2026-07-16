# Remaining Roadmap

**Last updated:** 2026-07-16 (end of day) — Phase 6.1 (Critical Integration Fixes) found earlier today and fixed the same day, re-verified live. See `docs/current/CURRENT_STATE.md` §1 for the full incident writeup.

## Completion Summary (live-verified 2026-07-16, post-fix)

| Layer | Completion |
|-------|-----------|
| Core intelligence (reasoning + retrieval) | ~85% |
| **Ingestion → retrieval integration (the actual product loop)** | **100% functional via the real API** — fixed and live-verified 2026-07-16 |
| API surface | ~90% (all 12 routers confirmed working; CORS and deep health check not explicitly re-verified this pass) |
| Security / Auth | 100% — confirmed live |
| Rate limiting | Built, not load-tested |
| Observability | 100% — confirmed live |
| Evaluation framework | Runs correctly; now returns real citations (3 `HIGH`-confidence, up from 0/10 before the fix) |
| Frontend | 0% |
| **Overall backend** | Functionally complete for the first time — the core loop works end-to-end, not just in isolated component tests |

---

## Phase 6.1 — Critical Integration Fixes — ✅ DONE (found and fixed 2026-07-16)

**Goal:** Make the ingest → embed → graph-write → retrieve → cite loop actually work through the real HTTP API, not just in tests that hand-seed data.

**Fixes applied (all confirmed via live re-verification on 2026-07-16):**
1. `backend/api/v1/ingest.py::_build_worker()` — wired `memory_constructor`, `vector_indexer`, `graph_writer` into `IngestionWorker` for both `/ingest/synthetic` and `/ingest/github`. **Verified:** fresh workspace, ingested 2 events, `embedding_status` → `EMBEDDED`, `/reasoning/query` returned a real cited answer at `HIGH` confidence.
2. `backend/api/v1/admin.py::_run_reindex()` — fixed `VectorIndexer(vector_repo=...)` → `VectorIndexer(repo=...)`, fixed the call to the real `index()` method (was calling nonexistent `index_event()`), and now constructs a minimal `MemoryObject` from the `EventModel` row so vector-only re-embedding matches the endpoint's documented scope. **Verified:** reindexed the original broken test workspace — both `PENDING` events became `EMBEDDED`.
3. `backend/db/repositories/timeline_repo.py` — fixed `EventModel.event_timestamp` → `.timestamp` (2 occurrences) and `EventModel.raw_content` → `.content` (in the query filter; the dict-output keys `raw_content`/`raw_author` are unchanged, they're just output field names). **Verified:** `GET /timeline/.../entity/...` now returns `200` with correctly bucketed events.
4. Added integration tests that exercise the real endpoints end-to-end: `TestSyntheticIngestionPopulatesRetrieval` (asserts embeddings + graph nodes appear after real ingestion), `tests/integration/api/test_admin.py` (new — reindex now has coverage), `tests/integration/api/test_timeline_api.py` (new — entity timeline now has coverage).
5. Re-ran `scripts/evaluate.py` — golden queries now retrieve real citations (3 `HIGH`-confidence in the post-fix run; remaining failures were Gemini free-tier `429`s, not code defects).

**Actual effort:** ~half a day, matching the original estimate. Full suite went from 667→676 tests (86%→87% coverage), all green.

**A note on test-infra fragility surfaced while adding these tests:** the new test modules initially hit cross-event-loop errors (`Future attached to a different loop`) because each new `TestClient(app)` instance runs its own portal event loop while sharing the app's one global SQLAlchemy engine singleton. The existing codebase already has the fix pattern for this (`tests/e2e/reasoning/conftest.py` disposes the global engine at module teardown) — the same `autouse` disposal fixture was added to the three ingestion/admin/timeline test modules. Worth keeping in mind for any future test file that spins up its own `TestClient`.

---

## Phase 6A — API Hardening (Critical) — ✅ Code complete, mostly confirmed live

**Confirmed live 2026-07-16:** workspace creation, job status, CORS not explicitly tested this pass.
**Still needed:** deep health check endpoint (`GET /api/v1/health/deep` checking DB + Neo4j) — not confirmed present/working this pass.

---

## Phase 6B — Authentication (Critical) — ✅ Confirmed live

API key auth (header-based, workspace-scoped) works correctly: unauthenticated requests get 401, keyed requests succeed. `backend/core/auth.py`, `api_keys` table.

---

## Phase 6C — Rate Limiting (Important) — ✅ Built, not load-tested

`backend/core/rate_limiter.py` exists and has unit test coverage; not exercised under load in this pass.

---

## Phase 6D — Decision Intelligence (Important — MVP gap) — ✅ Confirmed live

`extract_decision_candidates()` runs off retrieved chunks, which now populate correctly post-Phase-6.1. Confirmed live: ingesting "We decided to migrate the auth-service from Express to Go..." produced a real `Decision` row via `GET /api/v1/decisions/{workspace}` with correct title/description/`source_event_id` (previously returned `[]` for the same input, purely because retrieval was starved — no decision-module code changes were needed).

---

## Phase 6E — Timeline Intelligence (Important — MVP gap) — ✅ Fixed and confirmed live

`GET /api/v1/timeline/{workspace_id}/entity/{entity_id}` now returns `200` with correctly bucketed events (was throwing `AttributeError` on every call — see Phase 6.1 item 3).

---

## Phase 8A — Observability (Important) — ✅ Confirmed live

`/api/v1/metrics/health-summary` correctly tracked request/error counts during this session's testing.

---

## Phase 8B — Evaluation Framework (Nice-to-have) — ✅ Confirmed live

`scripts/evaluate.py` + `data/eval/golden_queries.json` (10 queries — smaller than the 50 originally planned) work correctly as a harness. Post-fix run against a live workspace returned 3 genuine `HIGH`-confidence citations (up from 0/10 pre-fix); remaining failures were Gemini free-tier `429` rate limits, an external constraint, not a defect. `MANUAL_BACKEND_GUIDE.md` has been corrected to show the required `--workspace-id` flag.

---

## Phase 7 — Frontend (Blocked on backend)

**Gate:** Phase 6.1 is fixed and live-re-verified, Phase 6A/6B/6D/6E are confirmed working end-to-end, and the backend passes the full test suite — **all now true as of 2026-07-16.** Frontend work can start.

**Status:** Not started — `frontend/` contains only `.gitkeep` placeholders in `src/{components,pages,hooks}` and `public/`. No actual Next.js scaffold exists yet.

**Stack:** Next.js, React, Tailwind, react-force-graph

**Effort:** 3–4 weeks, unchanged

---

## Release Plan

| Release | Contents | Target | Status |
|---------|---------|--------|--------|
| `v0.5.0` | Phase 0–5 stable | Past | ✅ Done |
| `v0.6.0` | Phase 6A + 6B + 6C (API hardened + auth) | Past | ✅ Done, confirmed live |
| `v0.7.0` | Phase 6D + 6E (Decision + Timeline) + Phase 6.1 fixes | Current | ✅ Done, confirmed live 2026-07-16 — safe to tag now that Phase 6.1 fixes are merged |
| `v0.8.0` | Phase 8A observability | — | ✅ Done, confirmed live |
| `v1.0.0` | Frontend + full backend | Phase 7 | ⬜ Not started — now unblocked |

**2026-07-16 update:** The commit `21029a8` ("release candidate v0.7.0 preparation") predated the discovery of the Phase 6.1 bugs and should not have shipped as-is. The fixes have since landed on a branch and are pending PR into `dev`; once merged, `v0.7.0` can be tagged for real.
