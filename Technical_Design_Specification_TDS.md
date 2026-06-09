# Technical Design Specification (TDS) - Company Brain

Version: 1.0
Status: Deprecated / Historical Reference
Parent Document: Company Brain Final Master Architecture v2.1

> **NOTE:** This document reflects the original technical design. The actual implementation differs significantly in Phase 4 and Phase 5 (using `pgvector` instead of Pinecone, deterministic routing instead of an LLM `QueryRouter`, and different folder layouts). See `docs/adr/0001-phase5-reconciliation.md` for full drift details.

## 1. Code Architecture: Folder-Level Ownership

The following structure defines the exact responsibilities of each module in the `backend/` directory.

```text
 backend/
  ├── api/
  │   └── v1/
  │        ├── query.py          # Entry point for NL queries, handles synthesis response.
  │        ├── config.py         # Config Registry endpoints.
  │        └── ingest.py         # Webhook endpoints for Slack, GitHub, etc.
 │   │
 │   ├── retrieval/
 │   │    ├── planner.py        # Generates multi-step retrieval plans based on intent.
 │   │    ├── vector_retriever.py # Interface for Pinecone/Milvus semantic search.
 │   │    ├── graph_retriever.py  # Cypher query builder for Neo4j traversals.
 │   │    ├── keyword_retriever.py # BM25 / PostgreSQL full-text search.
 │   │    ├── reranker.py       # Cross-encoder scoring for candidate snippets.
 │   │    └── scorer.py         # Heuristic scoring (freshness, authority).
 │   │
 │   ├── reasoning/
 │   │    ├── orchestrator.py   # High-level control flow between retrieval and synthesis.
 │   │    ├── decision_module.py # Logic for extracting and validating decision records.
 │   │    ├── dependency_module.py # Logic for mapping service/team dependencies.
 │   │    ├── timeline_module.py # Logic for chronological event reconstruction.
 │   │    └── composer.py       # LLM prompt engineering and output formatting.
 │   │
 │   ├── graph/
 │   │    ├── schema.py         # Neo4j node/edge definitions and constraints.
 │   │    └── transformer.py    # Converts relational events into graph nodes/edges.
 │   │
 │   ├── memory/
 │   │    ├── vector_store.py   # Connection management and index versioning.
 │   │    └── postgres_store.py # SQLAlchemy models and migration logic.
```

## 2. Class Design

### 2.1 QueryRouter
**Responsibility:** Classify incoming natural language queries into the defined taxonomy.
```python
class QueryRouter:
    def classify_query(self, query_text: str) -> QueryIntent:
        """Uses a small model to determine if the query is OWNERSHIP, TIMELINE, etc."""
        pass

    def extract_entities(self, query_text: str) -> List[EntityMention]:
        """Identifies potential people, services, or projects in the query."""
        pass
```

### 2.2 RetrievalPlanner
**Responsibility:** Build a sequence of tool calls based on the classified intent.
```python
class RetrievalPlanner:
    def build_plan(self, intent: QueryIntent, entities: List[EntityMention]) -> ExecutionPlan:
        """Determines if we need graph traversals, vector search, or both."""
        pass
```

### 2.3 EntityResolver
**Responsibility:** Resolve raw strings to canonical entity IDs.
```python
class EntityResolver:
    def resolve(self, raw_name: str, context: Optional[str] = None) -> UUID:
        """Check alias table, then fuzzy match, then embeddings."""
        pass
```

## 3. Data Architecture: Database Schemas

### 3.1 PostgreSQL (Relational)

**entity_aliases**
- `id`: UUID (PK)
- `entity_id`: UUID (FK -> entities.id)
- `alias`: VARCHAR(255)
- `confidence`: FLOAT
- `created_at`: TIMESTAMP

**entity_relationships**
- `id`: UUID (PK)
- `source_entity_id`: UUID (FK)
- `target_entity_id`: UUID (FK)
- `relationship_type`: VARCHAR(50) (e.g., 'OWNS', 'DEPENDS_ON')
- `confidence`: FLOAT
- `evidence_id`: UUID (FK -> events.id)

**evidence**
- `id`: UUID (PK)
- `event_id`: UUID (FK)
- `chunk_id`: VARCHAR(100)
- `source_type`: VARCHAR(50)
- `authority_score`: FLOAT

### 3.2 Neo4j (Graph)

**Nodes:**
- `(:Person {id, name, email})`
- `(:Team {id, name})`
- `(:Service {id, name, type})`
- `(:Decision {id, title, status})`

**Relationships:**
- `(:Team)-[:OWNS]->(:Service)`
- `(:Service)-[:DEPENDS_ON]->(:Service)`
- `(:Person)-[:MEMBER_OF]->(:Team)`
- `(:Decision)-[:AFFECTS]->(:Service)`

**Constraints:**
```cypher
CREATE CONSTRAINT entity_id_unique FOR (n:Entity) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT service_name_unique FOR (s:Service) REQUIRE s.name IS UNIQUE;
```

### 3.3 Vector Store (PostgreSQL with pgvector)

**memory_objects table:**
```json
{
  "vector_id": "uuid",
  "entity_id": "uuid",
  "chunk_id": "uuid",
  "workspace_id": "uuid",
  "embedding_version": "v1.0.0",
  "content_type": "slack|github|doc",
  "created_at": "iso8601"
}
```

## 4. Operational Architecture: Retrieval Logic

### 4.1 Heuristic Weighting
The `RetrievalOrchestrator` applies weights based on `QueryType`:

| Query Type | Graph Weight | Vector Weight | Keyword Weight |
| :--- | :---: | :---: | :---: |
| OWNERSHIP | 0.7 | 0.2 | 0.1 |
| TIMELINE | 0.3 | 0.5 | 0.2 |
| DECISION | 0.2 | 0.6 | 0.2 |
| DEPENDENCY| 0.8 | 0.1 | 0.1 |

### 4.2 Query Classification Taxonomy
1. **OWNERSHIP**: Who owns/maintains X?
2. **DEPENDENCY**: What depends on X? What does X use?
3. **DECISION**: Why was X changed? What was the decision for Y?
4. **TIMELINE**: What is the history of X?
5. **INCIDENT**: What happened during the outage of X?
6. **PROJECT_STATUS**: What is the current state of project Y?
7. **PERSON_CONTEXT**: What has person Z been working on?
8. **CHANGE_HISTORY**: How has service X evolved?
9. **DOCUMENT_SEARCH**: Find documents related to topic T.
10. **GENERAL_SEARCH**: Unclassified informational queries.
