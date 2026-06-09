# Purpose:      Unit tests for memory/embeddings.py
# Tests:        embed_text validation — empty input, whitespace rejection.
#               Does NOT call Ollama in unit tests — integration tests do that.
# Run with:     pytest tests/unit/memory/test_embeddings.py -v

import pytest
from unittest.mock import MagicMock, patch

from backend.memory.embeddings import EMBEDDING_DIM, embed_text


class TestEmbedText:
    def test_empty_string_raises(self):
        with pytest.raises(ValueError, match="non-empty"):
            embed_text("")

    def test_whitespace_only_raises(self):
        with pytest.raises(ValueError, match="non-empty"):
            embed_text("   ")

    def test_returns_list_of_floats(self):
        fake_embedding = [0.1] * EMBEDDING_DIM
        mock_response = MagicMock()
        mock_response.embeddings = [fake_embedding]

        with patch("backend.memory.embeddings.ollama.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.embed.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = embed_text("test content about auth-service")

        assert isinstance(result, list)
        assert len(result) == EMBEDDING_DIM
        assert all(isinstance(v, float) for v in result)

    def test_embedding_dim_constant_is_768(self):
        assert EMBEDDING_DIM == 768

    def test_calls_ollama_with_correct_model(self):
        fake_embedding = [0.1] * EMBEDDING_DIM
        mock_response = MagicMock()
        mock_response.embeddings = [fake_embedding]

        with patch("backend.memory.embeddings.ollama.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.embed.return_value = mock_response
            mock_client_class.return_value = mock_client
            from backend.core.config import get_settings
            get_settings.cache_clear()

            embed_text("some content")

            mock_client.embed.assert_called_once()
            call_kwargs = mock_client.embed.call_args
            # Model argument should be from config (nomic-embed-text default)
            assert "nomic-embed-text" in str(call_kwargs)
