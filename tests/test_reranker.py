"""Tests for cross-encoder reranker."""
import pytest
from unittest.mock import patch, MagicMock
from tests.conftest import make_chunk
from src.core.reranker import rerank


class TestRerank:
    def test_sorts_by_rerank_score_descending(self):
        """Chunks are returned sorted by rerank_score, highest first."""
        chunks = [
            make_chunk(text="C", rerank_score=0.0),
            make_chunk(text="A", rerank_score=0.0),
            make_chunk(text="B", rerank_score=0.0),
        ]
        # Mock predict to return scores [1.0, 9.0, 5.0]
        mock_model = MagicMock()
        mock_model.predict.return_value = [1.0, 9.0, 5.0]

        with patch("src.core.reranker._reranker._model", mock_model):
            result = rerank("test query", chunks, top_k=3)

        assert [c.text for c in result] == ["A", "B", "C"]

    def test_top_k_limits_output(self):
        """Only top_k chunks are returned."""
        chunks = [make_chunk(text=str(i), rerank_score=0.0) for i in range(6)]
        mock_model = MagicMock()
        mock_model.predict.return_value = [float(i) for i in range(6)]

        with patch("src.core.reranker._reranker._model", mock_model):
            result = rerank("query", chunks, top_k=3)

        assert len(result) == 3

    def test_rerank_score_set_on_chunks(self):
        """rerank_score field is populated from cross-encoder output."""
        chunk = make_chunk(text="legal text", rerank_score=0.0)
        mock_model = MagicMock()
        mock_model.predict.return_value = [7.42]

        with patch("src.core.reranker._reranker._model", mock_model):
            result = rerank("query", [chunk], top_k=1)

        assert abs(result[0].rerank_score - 7.42) < 0.001

    def test_empty_chunks_returns_empty(self):
        """Empty input returns empty list without calling the model."""
        mock_model = MagicMock()
        with patch("src.core.reranker._reranker._model", mock_model):
            result = rerank("query", [], top_k=5)

        assert result == []
        mock_model.predict.assert_not_called()
