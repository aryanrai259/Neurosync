# backend/graph

## Purpose
Extracts entities and relationships from `NormalizedEvent` objects and
builds the Neo4j knowledge graph. This is what makes Company Brain able to
answer relationship-based questions ("who worked on X?", "what decisions
led to Y?").

## Responsibilities
- Extract named entities from event content (people, services, tickets, PRs)
- Identify relationships between entities (authored, discussed, decided, depends_on)
- Write entity nodes and relationship edges to Neo4j
- Provide graph query helpers for the retrieval layer

## Files (to be added)
| File | Responsibility |
|---|---|
| `transformer.py` | Converts `NormalizedEvent` → graph nodes + edges |
| `entity_extractor.py` | NLP/LLM-based entity extraction from text |
| `relationship_builder.py` | Infers relationships between extracted entities |
| `neo4j_client.py` | Neo4j driver wrapper (queries, writes, transactions) |
| `schema.py` | Defines node labels and relationship types |

## Dependency Arrow
```
ingestion/ (NormalizedEvent)
  ↓
graph/transformer.py
  ├── graph/entity_extractor.py   (LLM/NER)
  ├── graph/relationship_builder.py
  └── graph/neo4j_client.py       → Neo4j
        ↑
retrieval/graph_retriever.py (reads from Neo4j)
```

## Inputs
- `NormalizedEvent` from ingestion pipeline

## Outputs
- Graph nodes written to Neo4j: `Person`, `Service`, `Decision`, `Event`, `Repository`, `Ticket`
- Graph edges: `AUTHORED`, `DISCUSSED`, `DECIDED`, `DEPENDS_ON`, `MENTIONED_IN`

## Dependencies
- `models/event.py`
- `models/entity.py`
- `core/database.py` (Neo4j connection)
- `core/config.py`

## Future Extensions
- Temporal graph (track how relationships evolve over time)
- Confidence scoring on extracted relationships
- Community detection (team/project clustering)
- Graph schema versioning + migrations

## Example Flow
```
NormalizedEvent(
  source="github",
  content="Merged PR #234: Move session storage to Redis",
  author="alice@company.com"
)
  → entity_extractor.py → ["alice", "Redis", "session storage", "PR #234"]
  → relationship_builder.py → alice AUTHORED PR#234, PR#234 MENTIONS Redis
  → neo4j_client.py → nodes + edges written to graph
```
