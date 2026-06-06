# backend/memory

Phase 4A–4B: Memory Construction and Vector Indexing

## Purpose

Converts a `NormalizedEvent` (output of Phase 3) into a structured `MemoryObject`,
then optionally indexes it into PgVector for semantic retrieval.

## Module Map

| File | Responsibility |
|------|----------------|
| `memory_object.py` | `MemoryObject`, `EntityRef`, `RelationshipRef` — the in-memory transport types |
| `entity_resolver.py` | Three-tier deterministic entity extraction (structured fields → seed lists → regex) |
| `relationship_extractor.py` | Seven named deterministic relationship rules |
| `memory_constructor.py` | Orchestrates resolution, extraction, and persistence for one event |
| `embeddings.py` | Generates vector embeddings via local Ollama (`nomic-embed-text`) |
| `vector_indexer.py` | Embeds a MemoryObject's content and stores it in the `event_embeddings` PgVector table |

## Data Flow

```
NormalizedEvent
      │
      ▼
 EntityResolver          <- Tier 1: structured fields (confidence=1.0)
      │                  <- Tier 2: seed list exact match (confidence=1.0)
      │                  <- Tier 3: regex pattern match (confidence=0.85)
      ▼
[EntityRef, ...]
      │
      ▼
RelationshipExtractor    <- 7 named rules: AUTHORED, AFFECTS, DISCUSSED_IN,
      │                                    REFERENCES, OWNS, DEPENDS_ON, RELATED_TO
      ▼
MemoryObject (frozen Pydantic model)
      │
      +---> memory_objects table (PostgreSQL, write-once audit log)
      +---> event_embeddings table (PgVector, Phase 4B)
      +---> graph/writer.py (Neo4j projection, Phase 4C)
```

## Extraction Tiers

### Tier 1: Structured Fields (confidence=1.0)
- `author_id` to PERSON entity (if not "bot", "system", "unknown")
- GitHub `metadata.repo` to REPOSITORY entity
- GitHub `metadata.labels` containing "decision"/"adr" to DECISION entity

### Tier 2: Seed Lists (confidence=1.0)
- `KNOWN_SERVICE_NAMES` from `ingestion/constants.py`
- `KNOWN_TEAM_NAMES` from `ingestion/constants.py`
- Built-in tech names: redis, postgres, kafka, etc.

### Tier 3: Regex Patterns (confidence=0.85)
- Jira/Linear tickets: `[A-Z]{2,10}-\d{1,6}` to TICKET
- Slack @mentions: `@username` to PERSON

## Relationship Rules

| Rule | Predicate | Condition |
|------|-----------|-----------|
| `_rule_authored` | AUTHORED | structured_author_id person -> event |
| `_rule_affects` | AFFECTS | event -> service mention |
| `_rule_discussed_in` | DISCUSSED_IN | service -> event |
| `_rule_references` | REFERENCES | event -> ticket mention |
| `_rule_owns` | OWNS | team + service co-occurrence (conf=0.6) |
| `_rule_depends_on` | DEPENDS_ON | GitHub + exactly 2 services (conf=0.7) |
| `_rule_related_to` | RELATED_TO | non-person co-occurrence fallback (conf=0.6) |

## Design Invariants

- `MemoryObject` is frozen. Downstream consumers must not mutate it.
- `entities` and `relationships` are always lists, never None.
- `memory_objects` table is write-once. Replay = `delete_by_event_id` then re-run.
- Phase 4A, 4B, and 4C are independently skippable — the worker continues on failure.
- No LLM extraction in Phase 4. All logic is deterministic and testable.
