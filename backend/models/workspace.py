# Purpose:      Canonical workspace model — the multi-tenancy boundary.
#               Every event, entity, query, and memory record carries a
#               workspace_id that references this model.
# Called By:    models/event.py, models/entity.py, models/query.py,
#               models/memory.py, models/ingestion.py,
#               api/, ingestion/, retrieval/, reasoning/
# Calls:        models/enums.py (SourceType, LLMProvider, VectorStore)
# Dependencies: pydantic v2, python stdlib (uuid, datetime, re)
# Test File:    tests/unit/models/test_workspace.py

import re
from datetime import datetime, timezone
from typing import List
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .enums import LLMProvider, SourceType, VectorStore


class WorkspaceConfig(BaseModel):
    """
    Per-workspace configuration.

    Embedded inside Workspace to avoid a separate DB join on every read.
    All fields have safe defaults so a Workspace can be created with zero config.
    """

    model_config = ConfigDict(frozen=True)

    enabled_sources: List[SourceType] = Field(
        default_factory=list,
        description="Which ingestion sources are active for this workspace.",
    )
    llm_provider: LLMProvider = Field(
        default=LLMProvider.OPENAI,
        description="Which LLM provider handles reasoning for this workspace.",
    )
    llm_model: str = Field(
        default="gpt-4o",
        min_length=1,
        description="Exact model name to pass to the LLM provider API.",
    )
    vector_store: VectorStore = Field(
        default=VectorStore.CHROMA,
        description="Which vector store backend holds embeddings for this workspace.",
    )
    retention_days: int = Field(
        default=365,
        ge=1,
        le=3650,
        description="How many days to retain ingested events (1–3650).",
    )
    max_context_tokens: int = Field(
        default=8000,
        ge=1000,
        le=128000,
        description="Maximum tokens to pass as context to the LLM per query.",
    )


class Workspace(BaseModel):
    """
    Canonical workspace — the top-level isolation boundary.

    All data in Company Brain is scoped to exactly one workspace.
    A workspace maps to one organisation / team using the system.
    """

    model_config = ConfigDict(frozen=True)

    id: UUID = Field(
        default_factory=uuid4,
        description="Globally unique workspace identifier.",
    )
    name: str = Field(
        min_length=1,
        max_length=128,
        description="Human-readable display name e.g. 'Acme Corp Engineering'.",
    )
    slug: str = Field(
        min_length=1,
        max_length=64,
        description="URL-safe identifier used in API paths e.g. 'acme-corp'.",
    )
    owner_id: str = Field(
        description="ID of the user who created and owns this workspace.",
    )
    config: WorkspaceConfig = Field(
        default_factory=WorkspaceConfig,
        description="Embedded workspace configuration.",
    )
    is_active: bool = Field(
        default=True,
        description="Soft-delete flag. Inactive workspaces are excluded from queries.",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of workspace creation.",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of last update.",
    )

    @field_validator("slug")
    @classmethod
    def slug_must_be_url_safe(cls, v: str) -> str:
        """
        Enforce slug rules:
        - Lowercase alphanumeric characters and hyphens only
        - Cannot start or end with a hyphen
        - No consecutive hyphens
        """
        pattern = r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$"
        if not re.match(pattern, v):
            raise ValueError(
                "slug must be lowercase alphanumeric with hyphens, "
                "no leading/trailing/consecutive hyphens"
            )
        if "--" in v:
            raise ValueError("slug cannot contain consecutive hyphens")
        return v
