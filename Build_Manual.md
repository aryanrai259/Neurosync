# Build Manual: Company Brain

Version: 1.0
Status: Deprecated / Execution Guide
Parent Document: Company Brain Final Master Architecture v2.1

> **NOTE:** This document reflects the original build plan. Actual implementation shifted from "Weeks" to "Phases" (0-8), adopted `pgvector` instead of Pinecone/Chroma, and uses a provider-agnostic LLM interface instead of strictly OpenAI. See `docs/adr/0001-phase5-reconciliation.md` for full drift details.

## 1. Overview
This manual provides a week-by-week execution plan to move from zero to a fully functional portfolio-ready demo.

## 2. Phase-by-Phase Execution Plan

### Phase 1-3: Foundation & Ingestion
*   **Goals:** Basic API, PostgreSQL schema, and synthetic data ingestion.
*   **Tasks:**
    *   Setup FastAPI project structure.
    *   Implement PostgreSQL models (Workspaces, Entities, Events).
    *   Create `scripts/seed_basic.py` to generate initial fake users and teams.
    *   Build a basic `/ingest` endpoint for Slack-like JSON payloads.

### Phase 4: Semantic & Structural Memory (Vector + Graph)
*   **Goals:** Embedding generation, basic semantic retrieval, and Neo4j integration.
*   **Tasks:**
    *   Setup PostgreSQL with `pgvector` (replacing Pinecone/ChromaDB).
    *   Setup Neo4j (local Docker).
    *   Implement hybrid retrieval merging Vector and Graph results.
    *   **Milestone:** System can answer "What is X?" based on Slack snippets.

### Phase 5: Reasoning Layer
*   **Goals:** Configuration Registry anchoring and Intent Routing.
*   **Tasks:**
    *   Implement Config Registry (Teams, Services, Repos).
    *   Implement deterministic `classifier.py` and rule-based `planner.py`.
    *   Implement `composer.py` with strict `tiktoken` context budgeting.
    *   Add provider-agnostic `llm_client.py`.
    *   **Milestone:** System can answer "Who owns auth-service?" using the pipeline.
    *   Implement `timeline_module.py` for chronological sorting.
    *   Implement `decision_module.py` to flag specific events as "Decisions".
    *   Build the `QueryRouter` to distinguish between "why" and "when".
    *   **Milestone:** System can answer "Why was the database migrated?"

### Week 5: Orchestration & UI (Frontend)
*   **Goals:** Unified retrieval and Next.js interface.
*   **Tasks:**
    *   Implement `RetrievalOrchestrator` to combine Graph + Vector results.
    *   Build Next.js dashboard with:
        *   Search Bar.
        *   Answer view with citations.
        *   Basic Graph visualization (e.g., using `react-force-graph`).
        *   Timeline component.

### Week 6: Polishing & Deployment
*   **Goals:** Observability, confidence scoring, and public hosting.
*   **Tasks:**
    *   Add confidence scoring heuristic.
    *   Setup logging and basic telemetry (Prometheus/Grafana or LangSmith).
    *   Deploy Backend to Railway/Render and Frontend to Vercel.
    *   Run final "AcmeCloud" synthetic dataset generation.

## 3. Development Prerequisites
- Python 3.11+
- Node.js 18+
- Docker (for local Postgres/Neo4j)
- LLM API Key (OpenAI, Gemini, or Anthropic configured via .env)
