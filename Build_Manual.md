# Build Manual: Company Brain

Version: 1.0
Status: Execution Guide
Parent Document: Company Brain Final Master Architecture v2.1

## 1. Overview
This manual provides a week-by-week execution plan to move from zero to a fully functional portfolio-ready demo.

## 2. Week-by-Week Execution Plan

### Week 1: Foundation & Ingestion
*   **Goals:** Basic API, PostgreSQL schema, and synthetic data ingestion.
*   **Tasks:**
    *   Setup FastAPI project structure.
    *   Implement PostgreSQL models (Workspaces, Entities, Events).
    *   Create `scripts/seed_basic.py` to generate initial fake users and teams.
    *   Build a basic `/ingest` endpoint for Slack-like JSON payloads.

### Week 2: Semantic Memory (Vector RAG)
*   **Goals:** Embedding generation and basic semantic retrieval.
*   **Tasks:**
    *   Integrate OpenAI/Cohere embedding API.
    *   Setup Vector Store (Pinecone or local ChromaDB).
    *   Implement `vector_retriever.py`.
    *   Create basic synthesis prompt in `composer.py`.
    *   **Milestone:** System can answer "What is X?" based on Slack snippets.

### Week 3: Structural Memory (GraphRAG)
*   **Goals:** Neo4j integration and relationship extraction.
*   **Tasks:**
    *   Setup Neo4j (local Docker or AuraDB).
    *   Implement `graph_transformer.py` to build nodes/edges from relational data.
    *   Implement `graph_retriever.py` with basic Cypher traversals.
    *   **Milestone:** System can answer "Who owns auth-service?" using the graph.

### Week 4: Reasoning & Temporal Logic
*   **Goals:** Timeline reconstruction and Decision tracking.
*   **Tasks:**
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
- Python 3.10+
- Node.js 18+
- Docker (for local Postgres/Neo4j)
- OpenAI API Key
- Pinecone/Milvus Account (optional, can use local alternatives)
