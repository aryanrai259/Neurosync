# Purpose:      Shared enumeration types used across all models.
#               Lives here so any model can import without circular dependencies.
# Called By:    models/workspace.py, models/event.py, models/entity.py,
#               models/ingestion.py, models/query.py
# Calls:        nothing
# Dependencies: Python stdlib (enum)
# Test File:    tests/unit/models/test_enums.py

from enum import Enum


class SourceType(str, Enum):
    """Canonical identifiers for every supported ingestion source."""

    SLACK = "slack"
    GITHUB = "github"
    JIRA = "jira"
    NOTION = "notion"
    EMAIL = "email"


class EntityType(str, Enum):
    """Categories of entities that can be extracted from events."""

    PERSON = "person"
    SERVICE = "service"
    REPOSITORY = "repository"
    TICKET = "ticket"
    DECISION = "decision"
    DOCUMENT = "document"
    TEAM = "team"


class LLMProvider(str, Enum):
    """Supported LLM providers (used in WorkspaceConfig and reasoning layer)."""

    OPENAI = "openai"
    GEMINI = "gemini"
    ANTHROPIC = "anthropic"


class VectorStore(str, Enum):
    """Supported vector store backends."""

    CHROMA = "chroma"
    QDRANT = "qdrant"


class RetrievalStrategy(str, Enum):
    """
    How the retrieval layer fetches context for a query.

    VECTOR: semantic similarity search against the vector store only.
    GRAPH:  relationship traversal against Neo4j only.
    HYBRID: both strategies combined, results reranked before returning.
            Default for all queries — best results in practice.
    """

    VECTOR = "vector"
    GRAPH = "graph"
    HYBRID = "hybrid"
