# backend/models

## Purpose
Canonical data types for Company Brain. Every other module imports from here.
No module should define its own data shapes — all schemas live in this directory.

## Responsibilities
- Define Pydantic models for all domain objects
- Define request/response schemas for the API layer
- Provide TypedDicts and enums for type safety across the codebase

## Files (Implemented in Phase 1)
| File | Contains |
|---|---|
| `enums.py` | `SourceType`, `EntityType`, `IngestionStatus`, `SyncStatus`, `EmbeddingStatus` |
| `event.py` | `NormalizedEvent` — canonical event from any source |
| `entity.py` | `Entity` — people, services, decisions |
| `query.py` | `QueryRequest`, `QueryResponse`, `RetrievedChunk` |
| `workspace.py` | `Workspace` |
| `memory.py` | `SessionContext`, `WorkspaceSnapshot` |
| `ingestion.py` | `IngestionRequest`, `IngestionResult`, `IngestionJob` |

## Dependency Arrow
```
models/ (this module — no dependencies on other backend modules)
  ↑
Everything else imports from here:
  ingestion/, retrieval/, reasoning/, graph/, memory/, api/, core/
```

## Design Decisions
- **Pydantic v2** for all models (validation, serialization, JSON schema generation)
- Models are **immutable** (frozen=True where applicable) — treat as value objects
- Every model has a `created_at: datetime` field for auditability
- `NormalizedEvent` is the single most important type — read it first

## Dependencies
- Pydantic v2
- Python `datetime`, `uuid`, `enum` (stdlib only)
- No other internal modules

## Future Extensions
- OpenAPI schema auto-generation from these models
- JSON Schema export for frontend TypeScript type generation
- Model versioning for backwards-compatible ingestion

## Example: NormalizedEvent shape (preview)
```python
class NormalizedEvent(BaseModel):
    id: UUID
    source: SourceType          # "slack" | "github" | "jira" | "notion"
    workspace_id: str
    content: str                # Raw text content
    author_id: str
    timestamp: datetime
    metadata: dict              # Source-specific extra fields
    created_at: datetime
```
