# Company Brain

> An AI-powered organizational memory system that ingests, structures, and retrieves institutional knowledge from tools like Slack, GitHub, Jira, Notion, and email.

---

## Current Project Status

**Completed:**
- Phase 0: Repository Setup
- Phase 1: Domain Models
- Phase 2: Database Layer
- Phase 3: Ingestion Pipeline

**Current Capabilities:**
- Create ingestion jobs
- Ingest synthetic events
- Ingest GitHub issues/PRs
- Normalize source events
- Deduplicate events
- Extract entities
- Persist events
- Persist entity registry
- Full test suite passing

**Test Status:**
- 414 tests passing
- 0 failed
- 0 warnings

**Next:**
- Phase 4: Vector + Graph Retrieval Layer

---

## Current Architecture

```text
GitHub
Slack (synthetic)
        │
        ▼
  Ingestion Layer
        │
        ▼
   PostgreSQL
        │
        ▼
      API
```

---

## Target Architecture

```text
GitHub
Slack
Jira
Notion
        │
        ▼
    Ingestion
        │
        ▼
    Postgres
    ChromaDB
      Neo4j
        │
        ▼
    Retrieval
        │
        ▼
    Reasoning
```

---

## Directory Structure

```text
neuro/
├── backend/
│   ├── api/
│   │   └── v1/
│   │       └── ingest.py       # FastAPI ingestion endpoints
│   ├── core/                   # Config, logging, DB session
│   ├── db/                     # DB models, alembic, repositories
│   ├── ingestion/
│   │   ├── adapters/
│   │   │   ├── base.py
│   │   │   ├── synthetic.py    # Pass-through synthetic adapter
│   │   │   └── github.py       # Live GitHub HTTP adapter
│   │   ├── normalizers/
│   │   │   ├── _parsing.py
│   │   │   ├── slack.py
│   │   │   ├── github.py
│   │   │   └── jira.py
│   │   ├── worker.py           # Orchestration logic
│   │   ├── schemas.py          # Adapter/API schemas
│   │   ├── constants.py
│   │   ├── deduplicator.py
│   │   └── entity_extractor.py
│   ├── models/                 # Canonical Pydantic domain models
│   ├── retrieval/              # (Planned) Vector, graph, hybrid
│   ├── reasoning/              # (Planned) Orchestrator, planner
│   ├── graph/                  # (Planned) Neo4j transformers
│   └── memory/                 # (Planned) Short-term session memory
├── frontend/                   # (Planned) Next.js chat interface
├── tests/
│   ├── integration/
│   └── unit/
├── docs/
├── scripts/
└── docker/
```

---

## Module Ownership

| Module | Status | Responsibility | Calls | Called By |
|---|---|---|---|---|
| `api/` | Implemented | HTTP surface | `ingestion/`, `reasoning/` | Client |
| `ingestion/` | Implemented | Raw → NormalizedEvent | `models/`, `db/` | `api/` |
| `db/` | Implemented | Database repositories | `models/` | `api/`, `ingestion/` |
| `models/` | Implemented | Canonical data types | — | Everything |
| `core/` | Implemented | Config, DB, logging | — | Everything |
| `retrieval/` | Planned | Fetch relevant context | `storage/*` | `reasoning/planner` |
| `reasoning/` | Planned | Plan + compose answers | `retrieval/*`, `graph/*` | `api/` |
| `graph/` | Planned | Entity extraction | `models/entity` | `ingestion/`, `reasoning/` |
| `memory/` | Planned | Session + long-term memory | `storage/postgres` | `reasoning/orchestrator` |

---

## Development Rules (Enforced)

1. **One file per responsibility** — no 500-line god files
2. **Every file has a header block** — Purpose / Called By / Calls / Dependencies
3. **Every directory has a README.md** — before any code is added
4. **No magic `utils/` folder** — helpers belong to their domain
5. **Design doc before code** — Purpose → Tests → Implementation
6. **Max 300–400 lines per file** — split before you exceed this
7. **Every commit includes a Why** — not just what changed

---

## Getting Started

### Prerequisites
- Python 3.11+
- Docker & Docker Compose
- (Optional) GitHub Token for live integration

### Environment Setup
1. Copy `.env.example` to `.env`
2. Update `GITHUB_TOKEN` in `.env` if testing the GitHub adapter.
3. Install dependencies:
```bash
python -m venv .venv
source .venv/bin/activate  # Or .venv\Scripts\activate on Windows
pip install -r requirements-dev.txt
```

### Database Setup
```bash
docker compose up -d
alembic upgrade head
```

### Running Tests
```bash
pytest tests/ -v
```

### Starting API
```bash
uvicorn backend.main:app --reload
```

---

## API Documentation

### `POST /api/v1/ingest/synthetic`
Accepts pre-formed generic raw events and processes them synchronously for deduplication and persistence.

**Request Body:**
```json
{
  "workspace_id": "123e4567-e89b-12d3-a456-426614174000",
  "requested_by": "test-runner",
  "events": [
    {
      "source": "slack",
      "source_id": "msg-001",
      "raw_content": "auth-service is down",
      "raw_author": "alice",
      "raw_timestamp": "2025-01-15T14:22:00Z"
    }
  ]
}
```

### `POST /api/v1/ingest/github`
Fires an asynchronous background worker that uses the GitHub REST API to fetch recent issues and PRs.

**Request Body:**
```json
{
  "workspace_id": "123e4567-e89b-12d3-a456-426614174000",
  "requested_by": "test-runner",
  "repo": "owner/repo"
}
```

### `GET /health`
Returns system health status.

---

## Phase Tracker

| Phase | Name | Status |
|---|---|---|
| 0 | Repo initialization + architecture | ✅ Done |
| 1 | Core domain models | ✅ Done |
| 2 | Database layer & migrations | ✅ Done |
| 3 | Ingestion pipeline | ✅ Done |
| 4 | Vector + graph retrieval | ⬜ Not started |
| 5 | Reasoning layer | ⬜ Not started |
| 6 | API layer | 🟡 In Progress |
| 7 | Frontend | ⬜ Not started |
| 8 | Evaluation + observability | ⬜ Not started |

---

## References

- [Implementation Plan](./Implementation_Plan.md)
- [Technical Design Specification](./Technical_Design_Specification_TDS.md)
- [Architecture Document](./company_brain_final_master_architecture.md)
- [Build Manual](./Build_Manual.md)
