# backend/api

## Purpose
HTTP surface layer for Company Brain. Exposes all external-facing endpoints.
Each file in this directory handles exactly one resource — no business logic lives here.

## Responsibilities
- Route incoming HTTP requests to the appropriate reasoning or ingestion handler
- Validate request shapes (delegated to Pydantic models)
- Return structured HTTP responses
- Handle authentication middleware

## Files (to be added)
| File | Route | Responsibility |
|---|---|---|
| `query.py` | `POST /query` | Natural language query endpoint |
| `ingest.py` | `POST /ingest` | Manual event ingestion |
| `health.py` | `GET /health` | Health + readiness check |
| `auth.py` | middleware | JWT validation |

## Dependency Arrow
```
Client
  ↓
api/ (this module)
  ↓
reasoning/orchestrator.py
```

## Inputs
- HTTP requests (JSON body, headers)

## Outputs
- HTTP responses (JSON)

## Dependencies
- `reasoning/orchestrator.py`
- `core/auth.py`
- `models/` (Pydantic schemas)

## Future Extensions
- WebSocket support for streaming responses
- Rate limiting middleware
- API versioning (`/v1/`, `/v2/`)

## Example Flow
```
POST /query
  → api/query.py
  → reasoning/orchestrator.py
  → [planner → retriever → composer]
  → JSON response
```
