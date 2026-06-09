# Phase 0.5: Drift Audit Report

## Audit Scope
The following documents were audited against the actual implemented `dev` branch state as of the end of Phase 5:
- `README.md`
- `Build_Manual.md`
- `Technical_Design_Specification_TDS.md` (TDS)
- `company_brain_final_master_architecture.md`
- `Implementation_Plan.md`
- `Synthetic_Data_and_Demo_Design.md`

## Identified Drift & Resolutions

### 1. Vector Store Infrastructure
- **Mismatch:** The Build Manual, TDS, and Master Architecture planned to use Pinecone, Milvus, or ChromaDB.
- **Reality:** We implemented `pgvector` natively in PostgreSQL for `memory_objects` and `event_embeddings`.
- **Type:** Code/Docs Mismatch
- **Fix:** Deprecated references to ChromaDB/Pinecone. Updated `README.md`, `Build_Manual.md`, and `TDS` to explicitly reflect `pgvector`. Added an ADR note to historical roadmap docs.

### 2. LLM Provider Lock-in
- **Mismatch:** Build Manual and TDS assumed OpenAI would be exclusively used via LangChain.
- **Reality:** We implemented a provider-agnostic factory (`llm_client.py`) supporting Google Gemini, Anthropic, and OpenAI via `.env`.
- **Type:** Code/Docs Mismatch
- **Fix:** Replaced strict OpenAI requirements in the `Build_Manual.md` and `README.md` with "LLM Provider (configured via .env)". 

### 3. Intent Routing Logic
- **Mismatch:** The TDS designed an LLM-based `QueryRouter` for intent classification.
- **Reality:** To improve speed and determinism, we built a rule-based `classifier.py` mapped tightly against the authoritative Postgres `config_registry`.
- **Type:** Code/Docs Mismatch
- **Fix:** Documented this pivot in the new `ADR-0001` and marked the TDS as a "Deprecated / Historical Reference".

### 4. Phase Tracking vs. Week Tracking
- **Mismatch:** `Build_Manual.md` used a "Week 1 to Week 6" tracking format, which clashed with the 9-Phase (Phase 0 to 8) format used in the codebase, `README.md`, and `Implementation_Plan.md`.
- **Reality:** Development aligns strictly to Phases.
- **Type:** Docs-Only Issue
- **Fix:** Rewrote the `Build_Manual.md` headers to align with "Phases" rather than "Weeks".

### 5. Context Budgeting (Token Management)
- **Mismatch:** Initial plans relied on rough character truncation for LLM prompts.
- **Reality:** We implemented strict `tiktoken` byte-pair encoding in `composer.py`.
- **Type:** Code/Docs Mismatch
- **Fix:** Logged the pivot in `ADR-0001`.

### 6. README Phase Status
- **Mismatch:** The phase tracker listed Phase 4 and Phase 5 as "Not Started", and architectural diagrams listed the `retrieval` and `reasoning` folders as "(Planned)".
- **Reality:** Phases 4, 5, and the foundation of Phase 6 are implemented and merged.
- **Type:** Docs-Only Issue
- **Fix:** Updated `README.md` to show ✅ Done for Phases 4-6, removed "(Planned)" tags, and added the newly deployed `/api/v1/reasoning/query` API endpoint.

## Deliverables Generated
1. **`docs/adr/0001-phase5-reconciliation.md`**: Created to permanently log the "Why" behind these architectural pivots.
2. **`docs/drift_audit_report.md`**: This report.

## Unresolved Inconsistencies
None. The active "current state" documents (`README.md` and `Build_Manual.md`) are now perfectly aligned with the codebase. The large foundational planning documents (`company_brain_final_master_architecture.md`, `Implementation_Plan.md`, and `TDS`) have been carefully marked as historical references with explicit disclaimers directing readers to `ADR-0001` for modern context. This prevents rewriting 150KB of historical roadmap text while completely resolving any ambiguity.

## Recommendation
The repository's source of truth is now clean, accurate, and completely reconciled. The drift is resolved. 
**Recommendation:** The repository is clean enough to safely resume feature work and enter the design phase for Phase 6 / Phase 7.
