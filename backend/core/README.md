# backend/core

## Purpose
Foundational infrastructure for Company Brain. Contains configuration,
database connection management, logging, and shared utilities that are
domain-agnostic. Every other module imports from here — but core imports
from nothing else.

## Responsibilities
- Load and validate application configuration from environment variables
- Manage database connection pools (PostgreSQL, Redis, ChromaDB, Neo4j)
- Configure structured logging
- Provide authentication/JWT utilities
- Define application-wide constants and enums

## Files (Implemented)
| File | Responsibility |
|---|---|
| `config.py` | Pydantic Settings — all env vars, validated at startup |

*Note: Database connection pooling and sessions have been moved to their own dedicated domain at `backend/db/` to cleanly separate DB layer logic.*

## Dependency Arrow
```
core/ (this module — no internal dependencies)
  ↑
Everything imports from core:
  api/, ingestion/, retrieval/, reasoning/, graph/, memory/
```

## Inputs
- Environment variables (`.env` file or system env)
- Database connection strings

## Outputs
- Configured database clients (singletons)
- Application settings object
- Logger instances

## Dependencies
- `pydantic-settings`
- `sqlalchemy` (PostgreSQL)
- `redis-py`
- `neo4j` driver
- `chromadb` or `qdrant-client`
- `python-jose` (JWT)
- Python `logging` stdlib

## Future Extensions
- OpenTelemetry tracing setup
- Prometheus metrics endpoint
- Feature flags
- Secrets manager integration (AWS Secrets Manager / Vault)

## Example: Config preview
```python
class Settings(BaseSettings):
    database_url: str
    redis_url: str
    neo4j_uri: str
    openai_api_key: str
    vector_store: Literal["chroma", "qdrant"] = "chroma"
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env")
```
