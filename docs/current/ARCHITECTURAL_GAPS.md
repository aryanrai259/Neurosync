# Architectural Gap Analysis

## Missing Modules
- **Timeline Module:** Described in the Master Architecture as reconstructing chronological events, but `reasoning/timeline_module.py` was never implemented.
- **Decision Module:** Described as isolating ADRs and pivot points, but currently omitted. The system relies entirely on general semantic search to find decisions.

## Missing APIs
- **Admin / System Tools:** No APIs exist to force-sync the entire graph, drop the database, or trigger manual index rebuilds (`api/v1/admin.py` is absent).
- **Entity Resolution / Manual CRUD:** No endpoints exist to manually edit aliases or merge duplicate entities outside the configuration registry.

## Missing UI Components
- **Entire Frontend:** The repository contains no `frontend/` directory despite the architecture demanding a chat interface and graph visualization.

## Missing Tests
- **Live Retrieval Integration:** The `test_pipeline.py` relies on completely mocked retriever outputs. There is no end-to-end integration test asserting that a live Postgres pgvector query successfully pipes into the Gemini synthesis.

## Abandoned Ideas
- **LLM Intent Routing:** The idea of using an LLM to route queries (`QueryRouter`) was abandoned for speed and cost in favor of the deterministic classifier.

## Accidental Complexity
- **Two Build Guides:** The presence of both `Build_Manual.md` and `Implementation_Plan.md` caused significant confusion during the audit pass.
