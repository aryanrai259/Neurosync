# backend/memory

## Purpose
Manages two memory scopes for Company Brain:
1. **Short-term (session memory)** — tracks conversation context within a single user session
2. **Long-term (workspace memory)** — persists important decisions, summaries, and entity snapshots across sessions

## Responsibilities
- Store and retrieve conversation history for multi-turn queries
- Summarize long conversations to fit within LLM context windows
- Persist workspace-level knowledge summaries
- Provide memory context to the reasoning/orchestrator

## Files (to be added)
| File | Responsibility |
|---|---|
| `session_store.py` | CRUD for short-term session memory (Redis) |
| `workspace_memory.py` | Long-term workspace knowledge (PostgreSQL) |
| `summarizer.py` | Summarizes conversation history when it grows too long |
| `memory_manager.py` | Unified interface — orchestrator calls only this |

## Dependency Arrow
```
reasoning/orchestrator.py
  ↓
memory/memory_manager.py
  ├── memory/session_store.py     → Redis
  └── memory/workspace_memory.py → PostgreSQL
        ↓
reasoning/composer.py (receives memory context)
```

## Inputs
- `session_id: str` — identifies the conversation
- `workspace_id: str` — scopes long-term memory
- New messages to append to session

## Outputs
- `SessionContext` — recent messages + summary (for reasoning/composer)
- `WorkspaceSnapshot` — key facts + decisions for the workspace

## Dependencies
- `core/database.py` (Redis + PostgreSQL clients)
- `core/config.py`
- `models/memory.py`

## Future Extensions
- Episodic memory (remember past queries and their answers)
- User-specific memory profiles
- Memory decay / TTL policies
- Explainable memory ("I'm using this context because...")

## Example Flow
```
User asks: "What did we decide about the auth migration?"
  → orchestrator.py → memory_manager.py
  → session_store.py: last 5 messages in this session
  → workspace_memory.py: stored decision record for "auth migration"
  → combined context passed to composer.py
  → LLM answers with full historical awareness
```
