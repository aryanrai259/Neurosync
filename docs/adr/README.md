# docs/adr

## Purpose
Architecture Decision Records (ADRs) for Company Brain.
Every significant architectural decision — a database choice, a library selection,
a tradeoff — gets a numbered ADR file here.

## Format
Each ADR follows this template:

```markdown
# ADR-NNN: [Decision Title]

## Status
Proposed | Accepted | Deprecated | Superseded by ADR-XXX

## Context
What problem are we solving? What constraints exist?

## Decision
What did we decide?

## Consequences
What are the tradeoffs? What becomes easier? What becomes harder?

## Alternatives Considered
What else did we evaluate and why did we reject it?
```

## Index (to be added)
| ADR | Title | Status |
|---|---|---|
| ADR-001 | PostgreSQL as primary event store | Proposed |
| ADR-002 | ChromaDB as vector store | Proposed |
| ADR-003 | Neo4j as knowledge graph | Proposed |
| ADR-004 | FastAPI as HTTP framework | Proposed |
| ADR-005 | Redis for session memory | Proposed |

## Rule
If someone asks "why did we use X?", the answer must be in an ADR.
No verbal-only architectural decisions.
