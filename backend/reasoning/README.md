# backend/reasoning

## Purpose
The brain of Company Brain. Orchestrates the full query lifecycle:
receive → plan → retrieve → compose → respond.
No retrieval or storage logic lives here — this module only coordinates.

## Responsibilities
- Receive a natural language query from the API layer
- Decompose the query into a retrieval plan
- Coordinate retrieval across vector and graph stores
- Compose a final answer from retrieved context
- Manage multi-turn conversational context

## Files (to be added)
| File | Responsibility |
|---|---|
| `orchestrator.py` | Top-level query lifecycle coordinator |
| `planner.py` | Decomposes query → `RetrievalQuery` objects |
| `composer.py` | Assembles context chunks → final LLM prompt + response |
| `prompt_builder.py` | Constructs LLM prompts from templates + context |
| `decision_tracker.py` | Detects and records organizational decisions |

## Dependency Arrow (Full Query Flow)
```
api/query.py
  ↓
reasoning/orchestrator.py
  ├── memory/session_store.py   (fetch conversation history)
  ├── reasoning/planner.py      (decompose query)
  │     ↓
  │   retrieval/hybrid_retriever.py
  │     ↓
  │   List[RetrievedChunk]
  ↓
reasoning/composer.py
  ├── reasoning/prompt_builder.py
  └── LLM API (OpenAI / Gemini)
  ↓
api/query.py → HTTP response
```

## Inputs
- `QueryRequest` from `api/query.py`
  - `query: str` — user's natural language question
  - `workspace_id: str`
  - `session_id: str` (optional, for multi-turn)

## Outputs
- `QueryResponse`
  - `answer: str`
  - `sources: List[Source]`
  - `confidence: float`
  - `session_id: str`

## Dependencies
- `retrieval/` (all retrievers)
- `memory/session_store.py`
- `models/query.py`
- `core/config.py` (LLM provider, model name)
- `core/logging.py`

## Future Extensions
- Agentic loop (multi-step reasoning, tool use)
- Self-critique and answer verification
- Streaming response support
- Query routing (simple vs. complex queries)

## Example Flow
```
"Why did we switch auth to Redis?"
  → orchestrator.py
  → planner.py → [
      RetrievalQuery(entities=["auth", "Redis"], strategy="graph"),
      RetrievalQuery(keywords=["auth", "session", "Redis"], strategy="vector")
    ]
  → retrieval results merged + reranked
  → composer.py → prompt built → LLM called
  → "The auth service moved to Redis in Q3 2024 because..."
  → sources: [slack_msg_xyz, github_pr_123, jira_ticket_456]
```
