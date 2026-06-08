# Purpose:      Single source of truth for all application configuration.
#               Reads from environment variables / .env file at startup.
#               All defaults live here — nothing is hardcoded anywhere else.
# Called By:    Application code that creates model instances, DB clients,
#               LLM clients, ingestion workers, reasoning layer.
#               Never imported by models/ — models are pure data types.
# Calls:        models/enums.py (LLMProvider, VectorStore)
# Dependencies: pydantic-settings, python stdlib (functools)
# Test File:    tests/unit/core/test_config.py

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from backend.models.enums import LLMProvider, VectorStore


class Settings(BaseSettings):
    """
    Application configuration loaded from environment variables.

    Priority (highest → lowest):
      1. Actual environment variables (e.g. set in shell / Docker)
      2. .env file in the project root
      3. Defaults defined below

    Add new config keys here as new phases are built.
    Never hardcode values in other modules — always import from get_settings().
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",       # silently ignore unknown env vars
        case_sensitive=False, # DEFAULT_LLM_MODEL and default_llm_model both work
    )

    # ─── App ──────────────────────────────────────────────────────────────────
    app_name: str = Field(default="Company Brain", description="Application display name.")
    app_version: str = Field(default="0.1.0", description="Semantic version string.")
    debug: bool = Field(default=False, description="Enable debug mode (verbose logging, etc).")
    log_level: str = Field(default="INFO", description="Logging level: DEBUG | INFO | WARNING | ERROR.")

    # ─── LLM ──────────────────────────────────────────────────────────────────
    default_llm_provider: LLMProvider = Field(
        default=LLMProvider.OPENAI,
        description="Default LLM provider for the reasoning layer.",
    )
    default_llm_model: str = Field(
        default="gpt-4o",
        description="Default model name passed to the LLM provider API.",
    )

    # ─── Vector Store ─────────────────────────────────────────────────────────
    default_vector_store: VectorStore = Field(
        default=VectorStore.PGVECTOR,
        description="Default vector store backend for embeddings.",
    )

    # ─── Workspace Defaults ───────────────────────────────────────────────────
    default_retention_days: int = Field(
        default=365,
        ge=1,
        le=3650,
        description="Default number of days to retain ingested events.",
    )
    default_max_context_tokens: int = Field(
        default=8000,
        ge=1000,
        le=128000,
        description="Default maximum tokens to pass as context to the LLM.",
    )

    # ─── Phase 2 (Database) — uncomment when Phase 2 begins ──────────────────
    database_url: str = Field(default="postgresql+asyncpg://neuro_user:neuro_password@127.0.0.1:5433/neuro_db", description="PostgreSQL async connection string.")
    # redis_url: str = Field(default="redis://localhost:6379/0")
    # neo4j_uri: str = Field(default="bolt://localhost:7687")
    # neo4j_user: str = Field(default="neo4j")
    # neo4j_password: str = Field(default="")

    # ─── Phase 3 (Ingestion) ──────────────────────────────────────────────────
    github_token: str | None = Field(default=None, description="GitHub personal access token for ingestion adapter.")

    # ─── Phase 4A (Memory Construction) ──────────────────────────────────────
    # No additional config needed; uses existing DB connection.

    # ─── Phase 4B (Embeddings / PgVector) ────────────────────────────────────
    embedding_model: str = Field(
        default="nomic-embed-text",
        description="Ollama model name for generating embeddings.",
    )
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        description="Base URL of the local Ollama server.",
    )

    # ─── Phase 4C (Neo4j Graph) ───────────────────────────────────────────────
    neo4j_uri: str = Field(
        default="bolt://localhost:7687",
        description="Neo4j Bolt connection URI.",
    )
    neo4j_user: str = Field(
        default="neo4j",
        description="Neo4j username.",
    )
    neo4j_password: str = Field(
        default="neuro_password",
        description="Neo4j password.",
    )

    # ─── Phase 4 (LLM API Keys — unused until Phase 5) ───────────────────────
    # openai_api_key: str = Field(default="")
    # gemini_api_key: str = Field(default="")
    # anthropic_api_key: str = Field(default="")

    # ─── Phase 5 (Reasoning Layer LLM Config) ─────────────────────────────────
    llm_provider: str = Field(default="mock", description="LLM provider: mock, openai, anthropic, gemini, groq, etc.")
    llm_model: str = Field(default="mock-model", description="Specific model name to use.")
    llm_api_key: str | None = Field(default=None, description="API key for the provider.")
    llm_base_url: str | None = Field(default=None, description="Optional base URL for the LLM API.")
    llm_timeout_seconds: int = Field(default=30, description="Timeout for LLM API calls.")
    llm_temperature: float = Field(default=0.0, description="Temperature for the LLM generation.")


@lru_cache
def get_settings() -> Settings:
    """
    Returns a cached Settings instance.

    Using @lru_cache means the .env file is read exactly once per process.
    In tests, call get_settings.cache_clear() before each test to get fresh settings.
    """
    return Settings()
