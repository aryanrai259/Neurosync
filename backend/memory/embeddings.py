# Purpose:      Embedding wrapper — generates vector embeddings for event content.
#               Uses the Ollama local embedding server with the nomic-embed-text model.
#               Returns a list of floats (768 dimensions for nomic-embed-text).
#               All embedding logic is isolated here. Callers never import Ollama directly.
#               To swap the model, change only this file.
# Called By:    memory/vector_indexer.py
# Calls:        ollama Python SDK (local HTTP call to Ollama server)
#               core/config.py (ollama_base_url, embedding_model)
# Dependencies: ollama, python stdlib (logging)
# Test File:    tests/unit/memory/test_embeddings.py

import logging

import ollama

from backend.core.config import get_settings

logger = logging.getLogger(__name__)

# Dimension of nomic-embed-text embeddings.
# Used by vector_repo and Alembic migration to set the VECTOR column size.
EMBEDDING_DIM = 768


def embed_text(text: str) -> list[float]:
    """
    Generate a vector embedding for a text string using the configured model.

    Uses the synchronous Ollama client so this function can be called from
    an async context via asyncio.to_thread() in vector_indexer.py.

    Args:
        text: The text to embed. Must be non-empty.

    Returns:
        A list of floats with length EMBEDDING_DIM (768 for nomic-embed-text).

    Raises:
        ValueError: If text is empty or whitespace-only.
        ollama.ResponseError: If the Ollama server returns an error.
        httpx.ConnectError: If the Ollama server is not running.
    """
    if not text or not text.strip():
        raise ValueError("embed_text: text must be non-empty")

    settings = get_settings()
    model = settings.embedding_model
    base_url = settings.ollama_base_url

    client = ollama.Client(host=base_url)
    response = client.embed(model=model, input=text)
    embedding: list[float] = response.embeddings[0]

    logger.debug(
        "embed_text: model=%s dim=%d text_len=%d",
        model, len(embedding), len(text),
    )
    return embedding
