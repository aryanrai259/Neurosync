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

## Files (to be added)
| File | Responsibility |
|---|---|
| `config.py` | Pydantic Settings — all env vars, validated at startup |
| `database.py` | Connection pools for all databases (postgres, redis, neo4j, vector) |
| `logging.py` | Structured JSON logging setup (used by all modules) |
| `auth.py` | JWT validation, API key verification |
| `exceptions.py` | Custom exception classes (IngestionError, RetrievalError, etc.) |

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
