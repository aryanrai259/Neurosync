# Remaining Roadmap

**Last updated:** 2026-06-09 — Phase 5 closed, Phase 6 active

## Completion Summary (at Phase 5 close)

| Layer | Completion |
|-------|-----------|
| Core intelligence (reasoning + retrieval) | ~85% |
| API surface | ~35% |
| Security / Auth | 0% |
| Observability | 10% |
| Evaluation framework | 5% |
| Frontend | 0% |
| **Overall backend** | ~41% |

---

## Phase 6A — API Hardening (Critical)

**Goal:** Make the existing API surface complete, correct, and deployable.

**Gaps to close:**
- CORS middleware (`backend/main.py`)
- Deep health check endpoint (`GET /api/v1/health/deep`) — checks DB + Neo4j
- Workspace management (`POST /api/v1/workspaces`, `GET /api/v1/workspaces/{id}`)
- Job status endpoint (`GET /api/v1/jobs/{job_id}`)
- Admin endpoints (`POST /api/v1/admin/reset`, `POST /api/v1/admin/reindex`)

**Effort:** 2–3 days

---

## Phase 6B — Authentication (Critical)

**Goal:** No request reaches the reasoning pipeline without identity.

**Implementation:** API key auth (header-based, workspace-scoped). JWT upgrade later.

**Files:** `backend/core/auth.py`, auth middleware, `api_keys` table + migration

**Effort:** 1–2 days

---

## Phase 6C — Rate Limiting (Important)

**Goal:** Per-endpoint limits per the architecture spec (60 req/min for query, 1000 req/min for ingest).

**Files:** `slowapi` integration in `backend/main.py`

**Effort:** 4 hours

---

## Phase 6D — Decision Intelligence (Important — MVP gap)

**Goal:** The system can store, retrieve, and reason about organizational decisions.

**Gaps to close:**
- `decisions` table + Alembic migration
- `backend/db/models/decision.py`, `backend/db/repositories/decision_repo.py`
- `backend/reasoning/decision_module.py`
- `backend/api/v1/decisions.py`

**Effort:** 3 days

---

## Phase 6E — Timeline Intelligence (Important — MVP gap)

**Goal:** `GET /api/v1/timeline/{entity_id}` returns a chronological event history.

**Gaps to close:**
- `backend/db/repositories/timeline_repo.py` — time-range SQL queries
- `backend/reasoning/timeline_module.py` — chronological bucketing
- `backend/api/v1/timeline.py`

**Effort:** 3 days

---

## Phase 8A — Observability (Important)

**Goal:** Metrics, structured logs, query trace storage.

**Files:** `backend/core/telemetry.py`, Prometheus `/metrics` endpoint, JSON logging formatter, query trace table

**Effort:** 2 days

---

## Phase 8B — Evaluation Framework (Nice-to-have)

**Goal:** Automated retrieval + reasoning quality measurement.

**Files:** `data/eval/golden_queries.json` (50 queries), `scripts/evaluate.py`

**Effort:** 3 days

---

## Phase 7 — Frontend (Blocked on backend)

**Gate:** Begins only when Phase 6A, 6B, 6D, 6E are complete and the backend passes full test suite on `main`.

**Stack:** Next.js, React, Tailwind, react-force-graph

**Effort:** 3–4 weeks

---

## Release Plan

| Release | Contents | Target |
|---------|---------|--------|
| `v0.5.0` | Phase 0–5 stable (current) | ✅ Now |
| `v0.6.0` | Phase 6A + 6B + 6C (API hardened + auth) | Phase 6 sprint |
| `v0.7.0` | Phase 6D + 6E (Decision + Timeline) | Phase 6 sprint |
| `v0.8.0` | Phase 8A observability | Phase 8 sprint |
| `v1.0.0` | Frontend + full backend | Phase 7 |
