# ADR 0001: Phase 5 Documentation & Architecture Reconciliation

## Status
Accepted

## Context
During the completion of Phase 4 (Vector + Graph Retrieval) and Phase 5 (Reasoning Layer), the actual implemented architecture naturally evolved to meet operational requirements, differing from the original Master Architecture, Build Manual, and TDS. 
As we prepare to enter Phase 6 (API Layer), the historical documents were causing a drift in the source of truth.

## Detected Drift
1. **Vector Storage:** The original specs proposed Pinecone, Milvus, or ChromaDB. We implemented `pgvector` inside PostgreSQL (`memory_objects` and `event_embeddings` tables) to simplify operational overhead and keep vector data strongly consistent with relational events.
2. **Graph Projection:** Instead of using raw events, the Graph (Neo4j) is currently populated and anchored by the authoritative Configuration Registry (Teams, Services, Repositories).
3. **LLM Provider:** The specs relied exclusively on OpenAI. We implemented a provider-agnostic factory (`llm_client.py`) supporting Google Gemini, Anthropic Claude, and OpenAI via `.env` configuration.
4. **Phase Naming vs Weeks:** The `Build_Manual.md` tracked progress in "Weeks", while the codebase and implementation plan use "Phases" (0-8).
5. **Intent Routing:** The TDS proposed an LLM-based `QueryRouter`. For deterministic speed, we implemented a rule-based `classifier.py` mapped against the live Config Registry.
6. **Token Budgeting:** Replaced heuristic character counts with strict `tiktoken` byte-pair encoding in `composer.py`.

## Decisions
1. **Postgres as Primary Vector Store:** We officially adopt `pgvector` as the system's vector database. References to Pinecone/ChromaDB are deprecated.
2. **Provider-Agnostic LLM Layer:** The Reasoning layer strictly requires standard API signatures. Hardcoded OpenAI references are deprecated.
3. **Phase-Based Tracking:** All roadmaps will strictly adhere to the 9-Phase (0-8) structure. "Week" based tracking is deprecated.
4. **Documentation Updates:** `README.md`, `Build_Manual.md`, and `Technical_Design_Specification_TDS.md` have been updated to reflect these decisions. `company_brain_final_master_architecture.md` and `Implementation_Plan.md` have been annotated to direct readers to this ADR, preserving their historical context while acknowledging the drift.

## Consequences
- Reduces infrastructure complexity (no separate ChromaDB container).
- Ensures deterministic and fast query intent classification.
- Developers must use `alembic` for vector schema changes.
- Requires `tiktoken` for accurate context-window calculations.
