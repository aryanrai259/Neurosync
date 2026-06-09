# Company Brain / Neurosync

> An organizational intelligence platform that ingests fragmented company activity from tools like Slack, GitHub, and Jira, builds a connected knowledge graph and semantic memory, and answers natural-language questions with grounded, cited evidence.

---

## Current Project Status — Phase 5 Complete

**Phases 0–5 are complete and E2E-verified.**  
The core reasoning pipeline — Classify → Plan → Retrieve (Vector + Graph) → Merge → Synthesize → Cite — is fully wired with real PostgreSQL (pgvector) and Neo4j backends, proven by 5 live query traces with real Gemini LLM responses.

**Test Status:** 551 tests passing · 91% coverage

**In Progress:** Phase 6 — API hardening, authentication, admin tools, Timeline + Decision modules.

---

## Live Capabilities (Phase 0–5)

| Capability | Status |
|-----------|--------|
| Ingest synthetic events | ✅ |
| Ingest GitHub issues + PRs | ✅ |
| Normalize events (Slack, GitHub, Jira formats) | ✅ |
| Deduplicate events by checksum | ✅ |
| Extract entities (service, team, person, ticket, repo) | ✅ |
| Extract relationships (AUTHORED, AFFECTS, REFERENCES, DEPENDS_ON) | ✅ |
| Build embeddings (Ollama nomic-embed-text) | ✅ |
| Vector similarity search (pgvector cosine) | ✅ |
| Graph traversal (Neo4j AFFECTS, REFERENCES edges) | ✅ |
| Hybrid retrieval merge | ✅ |
| Intent classification (GRAPH_ONLY / HYBRID / VECTOR_ONLY) | ✅ |
| Retrieval planning (token-budgeted) | ✅ |
| LLM synthesis (multi-provider: Gemini, OpenAI, Anthropic, Groq) | ✅ |
| Citation validation | ✅ |
| Config registry + graph sync | ✅ |
| Basic API (3 routers) | ✅ |
| Authentication / RBAC | ❌ Phase 6 |
| Timeline intelligence | ❌ Phase 6 |
| Decision intelligence | ❌ Phase 6 |
| Admin tools (reset, reindex) | ❌ Phase 6 |
| Observability / metrics | ❌ Phase 8 |
| Evaluation framework | ❌ Phase 8 |
| Frontend | ❌ Phase 7 |

---

## Architecture

```text
Source Events (GitHub, Slack, synthetic)
        │
        ▼
  Ingestion Layer
  ├── Normalizers (Slack / GitHub / Jira)
  ├── Deduplicator (checksum)
  ├── Entity Extractor (3-tier: structured → seed-list → regex)
  └── Relationship Extractor (AUTHORED, AFFECTS, REFERENCES, DEPENDS_ON)
        │
        ├── PostgreSQL (events, entities, embeddings, jobs, config)
        └── Neo4j (graph: AFFECTS, REFERENCES, DEPENDS_ON edges)
        │
        ▼
  Retrieval Layer
  ├── Vector Search  (pgvector cosine similarity)
  ├── Graph Search   (Neo4j Cypher traversal)
  └── Hybrid Merge   (score fusion)
        │
        ▼
  Reasoning Layer
  ├── Classifier     (deterministic keyword + entity routing)
  ├── Planner        (token-budgeted retrieval plan)
  ├── Composer       (LLM synthesis from evidence only)
  └── Citation Validator (ground claims to retrieved chunks)
        │
        ▼
  REST API (FastAPI)
  ├── POST /api/v1/ingest/synthetic
  ├── POST /api/v1/ingest/github
  ├── POST /api/v1/reasoning/query
  ├── GET/POST /api/v1/config/*
  └── GET /health
```

---

## Directory Structure

```text
neuro/
├── backend/
│   ├── api/
│   │   └── v1/
│   │       ├── ingest.py       # Ingestion endpoints (synthetic + GitHub)
│   │       ├── reasoning.py    # Reasoning query + explain endpoints
│   │       └── config.py       # Config registry endpoints
│   ├── core/                   # Settings (pydantic-settings), DB session
│   ├── db/
│   │   ├── models/             # SQLAlchemy ORM models
│   │   └── repositories/       # Async repositories (8 repos)
│   ├── ingestion/
│   │   ├── adapters/           # SyntheticAdapter, GitHubAdapter
│   │   ├── normalizers/        # slack.py, github.py, jira.py, _parsing.py
│   │   ├── worker.py           # IngestionWorker orchestrator
│   │   ├── deduplicator.py
│   │   └── entity_extractor.py
│   ├── memory/
│   │   ├── entity_resolver.py  # 3-tier entity resolution
│   │   ├── relationship_extractor.py
│   │   ├── memory_constructor.py
│   │   ├── vector_indexer.py
│   │   └── embeddings.py       # Ollama embed_text
│   ├── retrieval/
│   │   ├── vector_search.py
│   │   ├── graph_search.py
│   │   └── hybrid.py
│   ├── reasoning/
│   │   ├── pipeline.py         # Full E2E orchestrator
│   │   ├── classifier.py
│   │   ├── planner.py
│   │   ├── composer.py
│   │   ├── citation.py
│   │   ├── llm_client.py       # Multi-provider LLM abstraction
│   │   └── schemas.py
│   ├── graph/
│   │   ├── client.py           # Neo4j driver singleton
│   │   ├── queries.py
│   │   ├── schema.py
│   │   └── writer.py
│   ├── config/
│   │   └── service.py          # Config registry + graph syncer
│   └── models/                 # Canonical Pydantic domain models
├── tests/
│   ├── unit/                   # Pure unit tests (no DB required)
│   ├── integration/            # Tests requiring PostgreSQL + Neo4j
│   └── e2e/                    # Full pipeline traces
├── docs/
│   ├── adr/                    # Architecture Decision Records
│   └── current/                # Live source of truth: CURRENT_STATE, TRACEABILITY_MATRIX, ROADMAP_REMAINING
├── scripts/
│   └── generate_retrieval_proof.py   # E2E proof runner (5 queries, real DBs)
└── alembic/                    # Database migrations
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- Docker (for PostgreSQL + Neo4j)
- Ollama running locally (`ollama serve`) for embeddings — or set `EMBEDDING_MODEL` to skip
- An LLM API key (Gemini, OpenAI, Anthropic, or Groq) for the reasoning layer

### Setup

```bash
# 1. Clone and enter
git clone https://github.com/aryanrai259/Neurosync.git
cd Neurosync

# 2. Create virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/macOS

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
copy .env.example .env
# Edit .env: set LLM_PROVIDER, LLM_MODEL, LLM_API_KEY

# 5. Start databases
docker compose up -d

# 6. Run migrations
alembic upgrade head

# 7. Start the API
uvicorn backend.main:app --reload
```

### Running Tests

```bash
# Full suite (requires PostgreSQL + Neo4j running)
pytest tests/ -v

# Unit tests only (no external dependencies)
pytest tests/unit/ -v

# With coverage report
pytest tests/ --cov=backend --cov-report=term-missing
```

---

## API Reference

### `POST /api/v1/reasoning/query`
Execute a natural language query against the knowledge base.

**Request:**
```json
{
  "workspace_id": "123e4567-e89b-12d3-a456-426614174000",
  "query": "Who owns auth-service?"
}
```

**Response:**
```json
{
  "query_id": "...",
  "answer_markdown": "Auth-service is owned by the Platform Team [event-id].",
  "retrieval_strategy": "GRAPH_ONLY",
  "citations": ["event-uuid-1"],
  "confidence": "HIGH",
  "execution_ms": 1247
}
```

### `POST /api/v1/ingest/synthetic`
Ingest pre-formed events (synthetic data, demos).

```json
{
  "workspace_id": "123e4567-e89b-12d3-a456-426614174000",
  "requested_by": "demo-script",
  "events": [
    {
      "source": "slack",
      "source_id": "msg-001",
      "raw_content": "auth-service is owned by Platform Team. Team lead is @alice.",
      "raw_author": "alice",
      "raw_timestamp": "2026-01-15T14:22:00Z"
    }
  ]
}
```

### `POST /api/v1/ingest/github`
Fetch and ingest recent issues + PRs from a GitHub repository.

```json
{
  "workspace_id": "123e4567-e89b-12d3-a456-426614174000",
  "requested_by": "admin",
  "repo": "owner/repository-name"
}
```

### `GET /health`
Basic liveness probe. Returns `{"status": "ok", "version": "0.5.0"}`.

### `GET/POST /api/v1/config/*`
Config registry endpoints — manage teams, services, and repositories that ground the knowledge graph.

---

## Phase Tracker

| Phase | Name | Status |
|-------|------|--------|
| 0 | Repo setup + architecture | ✅ Complete |
| 1 | Domain models | ✅ Complete |
| 2 | Database layer + migrations | ✅ Complete |
| 3 | Ingestion pipeline | ✅ Complete |
| 4 | Memory construction + Vector + Graph retrieval | ✅ Complete |
| 5 | Reasoning layer + Config registry | ✅ Complete |
| 6 | API hardening + Auth + Admin + Timeline + Decision | 🔄 In Progress |
| 7 | Frontend (Next.js) | ⬜ Not started |
| 8 | Evaluation + Observability | ⬜ Not started |

---

## Development Rules

1. **One file per responsibility** — no 500-line god files
2. **Every file has a header block** — `Purpose / Called By / Calls / Dependencies / Test File`
3. **Every directory has a `README.md`** — before any code is added
4. **No magic `utils/` folder** — helpers belong to their domain
5. **Design doc before code** — Purpose → Tests → Implementation
6. **Max 300–400 lines per file** — split before you exceed this
7. **Feature branches → dev → main** — never commit directly to main
8. **Full test suite must pass** before merging to dev, and before releasing to main

---

## Branch Workflow

```
feature/xxx → dev (incremental merges, full suite after each)
                 ↓
              main (tagged stable releases only)
```

- `main` = stable releases only (tagged `v0.x.0`)
- `dev` = integration branch, always passing tests
- `feature/xxx` = one feature per branch, short-lived

---

## References

- [Architecture Document](./company_brain_final_master_architecture.md) *(historical — see ADR-0001 for deviations)*
- [Technical Design Specification](./Technical_Design_Specification_TDS.md) *(historical reference)*
- [Implementation Plan](./Implementation_Plan.md)
- [Build Manual](./Build_Manual.md)
- [ADR-0001: Phase 5 Reconciliation](./docs/adr/0001-phase5-reconciliation.md)
- [Current State](./docs/current/CURRENT_STATE.md)
- [Roadmap Remaining](./docs/current/ROADMAP_REMAINING.md)
- [Retrieval Proof Report](./docs/current/retrieval_proof_report.md)
