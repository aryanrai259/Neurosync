# backend/db

## Purpose
The database layer for Company Brain. This module manages the connection to PostgreSQL and implements the repository pattern for interacting with database models.

## Responsibilities
- Define SQLAlchemy ORM models mapped to PostgreSQL tables
- Manage Alembic migrations
- Provide concrete Repository implementations for CRUD operations on domain models
- Handle database sessions and async engine configuration

## Structure (Implemented in Phase 2)
| Component | Description |
|---|---|
| `session.py` | Asynchronous SQLAlchemy engine, session maker, and dependency injection utilities |
| `models/base.py` | SQLAlchemy `Base` class with mixins (`TimestampMixin`, `UUIDMixin`) |
| `models/*.py` | SQLAlchemy ORM models (e.g., `WorkspaceModel`, `EventModel`) with indexes and constraints |
| `repositories/base.py` | Generic repository providing standard CRUD operations |
| `repositories/*_repo.py` | Domain-specific repositories managing upserts and constraints (e.g., `event_repo.py`) |
| `alembic/` | Alembic environment, migration configuration, and generated migration scripts (located in the project root) |

## Dependency Arrow
```
backend/db/ (this module)
  ↑
  Imports from `backend/models` and `backend/core`
  ↓
  Imported by `backend/memory`, `backend/ingestion`, `backend/retrieval` (in future phases)
```

## Design Decisions
- **Async PostgreSQL Driver**: Uses `asyncpg` for optimal performance.
- **Repository Pattern**: Abstracts SQLAlchemy logic away from the rest of the application. The rest of the app only interfaces with the repositories, isolating DB operations.
- **Upsert Logic**: Uses PostgreSQL native `ON CONFLICT DO UPDATE` capabilities for efficiency and avoiding double ingestion.
- **Alembic**: Used for database migrations with an async configuration.

## Dependencies
- SQLAlchemy 2.0+ (async)
- asyncpg
- Alembic
