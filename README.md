# Company Brain

> An AI-powered organizational memory system that ingests, structures, and retrieves institutional knowledge from tools like Slack, GitHub, Jira, Notion, and email.

---

## What This Is

Company Brain transforms fragmented organizational data into a queryable knowledge graph. Engineers can ask natural language questions and get answers grounded in real company history — decisions, code context, discussions, and documentation.

---

## Architecture Overview

```
Ingestion Sources
(Slack, GitHub, Jira, Notion, Email)
        │
        ▼
  Ingestion Layer
  (normalize → NormalizedEvent)
        │
        ▼
  Storage Layer
  (PostgreSQL + ChromaDB + Neo4j)
        │
        ▼
  Retrieval Layer
  (vector + graph + hybrid)
        │
        ▼
  Reasoning Layer
  (orchestrator → planner → composer)
        │
        ▼
  API Layer
  (FastAPI → /query, /ingest, /health)
        │
        ▼
  Frontend
  (Next.js chat interface)
```

---

## Directory Structure

```
neuro/
├── backend/
│   ├── api/            # FastAPI routes — one file per resource
│   ├── ingestion/      # Source adapters → NormalizedEvent
│   ├── retrieval/      # Vector, graph, hybrid retrieval
│   ├── reasoning/      # Orchestrator, planner, composer
│   ├── graph/          # Neo4j graph transformers
│   ├── memory/         # Short-term session + long-term memory
│   ├── models/         # Pydantic data models (canonical types)
│   └── core/           # Config, logging, database connections
├── frontend/           # Next.js chat interface
├── tests/              # Mirrors backend structure
├── docs/
│   ├── diagrams/       # Architecture + dependency + flow diagrams
│   └── adr/            # Architecture Decision Records
├── scripts/            # One-off ops/setup scripts
└── docker/             # Dockerfiles + compose configs
```

---

## Module Ownership

| Module | Responsibility | Calls | Called By |
|---|---|---|---|
| `api/` | HTTP surface | `reasoning/orchestrator` | Client |
| `ingestion/` | Raw → NormalizedEvent | `models/event` | Ingestion workers |
| `retrieval/` | Fetch relevant context | `storage/*` | `reasoning/planner` |
| `reasoning/` | Plan + compose answers | `retrieval/*`, `graph/*` | `api/` |
| `graph/` | Entity + relationship extraction | `models/entity` | `ingestion/`, `reasoning/` |
| `memory/` | Session + long-term memory | `storage/postgres` | `reasoning/orchestrator` |
| `models/` | Canonical data types | — | Everything |
| `core/` | Config, DB, logging | — | Everything |

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

> Setup instructions will be added as each phase is implemented.

---

## Phase Tracker

| Phase | Name | Status |
|---|---|---|
| 0 | Repo initialization + architecture | ✅ Done |
| 1 | Core models + database schema | ⬜ Not started |
| 2 | Ingestion pipeline | ⬜ Not started |
| 3 | Vector + graph retrieval | ⬜ Not started |
| 4 | Reasoning layer | ⬜ Not started |
| 5 | API layer | ⬜ Not started |
| 6 | Frontend | ⬜ Not started |
| 7 | Evaluation + observability | ⬜ Not started |

---

## References

- [Implementation Plan](./Implementation_Plan.md)
- [Technical Design Specification](./Technical_Design_Specification_TDS.md)
- [Architecture Document](./company_brain_final_master_architecture.md)
- [Build Manual](./Build_Manual.md)
