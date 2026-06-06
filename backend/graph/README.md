# backend/graph

Phase 4C: Graph Memory — Neo4j Projection

## Purpose

Writes entities and relationships from a `MemoryObject` into Neo4j as a graph projection.
Neo4j is a **projection of PostgreSQL**, not the source of truth.
If the graph is lost, it can be fully rebuilt by replaying all `memory_objects` rows.

## Module Map

| File | Responsibility |
|------|----------------|
| `client.py` | Neo4j async driver singleton — `get_driver()`, `close_driver()`, `verify_connectivity()` |
| `schema.py` | Idempotent constraint and index creation — call once at startup |
| `writer.py` | `GraphWriter.write(memory_object)` — upserts Event, entity, and relationship nodes |
| `queries.py` | Named read-only Cypher queries for retrieval (Phase 4D) |

## Node Types

| Label | Uniqueness Constraint |
|-------|----------------------|
| `Event` | `event_id` (UUID from PostgreSQL) |
| `Person` | `(workspace_id, canonical_name)` |
| `Team` | `(workspace_id, canonical_name)` |
| `Service` | `(workspace_id, canonical_name)` |
| `Repository` | `(workspace_id, canonical_name)` |
| `Ticket` | `(workspace_id, canonical_name)` |
| `Document` | `(workspace_id, canonical_name)` |

## Relationship Types

| Predicate | Meaning |
|-----------|---------|
| `AUTHORED` | Person authored an Event |
| `OWNS` | Team owns a Service |
| `DEPENDS_ON` | Service depends on another Service |
| `REFERENCES` | Event references a Ticket |
| `DISCUSSED_IN` | Service was discussed in an Event |
| `AFFECTS` | Event affects a Service |
| `RELATED_TO` | Generic co-occurrence fallback |

## Available Read Queries

| Function | Purpose |
|----------|---------|
| `find_events_by_entity` | All event_ids linked to a named entity |
| `find_neighborhood` | 1-2 hop entity neighborhood |
| `find_service_owners` | Teams owning a given service |

## Design Invariants

- All writes use `MERGE` — idempotent. Re-processing the same MemoryObject does not create duplicates.
- Confidence is updated to the higher value on `MERGE` match.
- The graph writer logs and continues if individual node/edge writes fail.
- `create_schema()` must be called once at application startup (FastAPI lifespan).
- All nodes and queries are workspace-scoped via `workspace_id`.

## Docker Setup

Neo4j is started with `docker-compose up -d`. The browser UI is at `http://localhost:7474`.
Default credentials: `neo4j` / `neuro_password` (set in `.env`).
