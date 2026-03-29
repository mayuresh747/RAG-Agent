"""Integration test for multi-agent retrieval orchestrator."""
import json
import pytest
from unittest.mock import patch, MagicMock, call
from src.core.multi_agent import multi_agent_retrieve
from src.core.retriever import RetrievalResult


def _make_chroma_result(texts, scores):
    """Build a fake ChromaDB search result dict."""
    n = len(texts)
    return {
        "ids":       [["id_" + str(i) for i in range(n)]],
        "documents": [list(texts)],
        "metadatas": [[{"source_file": f"file_{i}.pdf", "page_number": i+1,
                        "title": "", "chunk_index": i} for i in range(n)]],
        "distances": [[1.0 - s for s in scores]],
    }


class TestMultiAgentRetrieve:
    def test_returns_retrieval_result(self):
        """Happy path: returns a RetrievalResult with chunks and libraries_searched."""
        analysis_json = json.dumps({
            "mode": "C",
            "agencies_in_scope": ["RCW", "WAC"],
            "agency_relevance": {"RCW": 3, "WAC": 2},
            "top_k": 4,
            "requires_numerical_comparison": False,
        })

        # Mock OpenAI (analyzer call)
        mock_msg = MagicMock(); mock_msg.content = analysis_json
        mock_choice = MagicMock(); mock_choice.message = mock_msg
        mock_openai_resp = MagicMock(); mock_openai_resp.choices = [mock_choice]

        # Mock embed_query
        mock_vector = [0.1] * 10

        # Mock vector_store.search per collection
        rcw_result = _make_chroma_result(["RCW chunk 1", "RCW chunk 2"], [0.8, 0.7])
        wac_result = _make_chroma_result(["WAC chunk 1"], [0.6])

        def fake_search(collection_name, *args, **kwargs):
            if "rcw" in collection_name:
                return rcw_result
            return wac_result

        with patch("src.core.analyzer.OpenAI") as MockOpenAI, \
             patch("src.core.multi_agent.embed_query", return_value=mock_vector), \
             patch("src.core.multi_agent.vector_search", side_effect=fake_search), \
             patch("src.core.multi_agent.rerank", side_effect=lambda q, chunks, top_k: chunks[:top_k]):

            MockOpenAI.return_value.chat.completions.create.return_value = mock_openai_resp
            result = multi_agent_retrieve("EV charging conflicts", min_score=0.1)

        assert isinstance(result, RetrievalResult)
        assert result.query == "EV charging conflicts"
        assert len(result.chunks) > 0
        assert len(result.libraries_searched) == 2
        assert result.total_candidates >= 3

    def test_min_score_filters_low_cosine_chunks(self):
        """Chunks with cosine < min_score are excluded before reranking."""
        analysis_json = json.dumps({
            "mode": "A",
            "agencies_in_scope": ["RCW"],
            "agency_relevance": {"RCW": 3},
            "top_k": 2,
            "requires_numerical_comparison": False,
        })
        mock_msg = MagicMock(); mock_msg.content = analysis_json
        mock_choice = MagicMock(); mock_choice.message = mock_msg
        mock_openai_resp = MagicMock(); mock_openai_resp.choices = [mock_choice]

        # Two chunks: one above 0.5 min_score, one below
        chroma_result = _make_chroma_result(["good chunk", "bad chunk"], [0.8, 0.05])

        with patch("src.core.analyzer.OpenAI") as MockOpenAI, \
             patch("src.core.multi_agent.embed_query", return_value=[0.1] * 10), \
             patch("src.core.multi_agent.vector_search", return_value=chroma_result), \
             patch("src.core.multi_agent.rerank", side_effect=lambda q, chunks, top_k: chunks[:top_k]):

            MockOpenAI.return_value.chat.completions.create.return_value = mock_openai_resp
            result = multi_agent_retrieve("landlord notice", min_score=0.5)

        assert result.total_candidates == 1  # only "good chunk" passed the filter
        assert result.chunks[0].text == "good chunk"
