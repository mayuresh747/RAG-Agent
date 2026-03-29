"""Tests for query intent analyzer."""
import json
import pytest
from unittest.mock import patch, MagicMock
from src.core.analyzer import analyze_query, AnalysisResult


def _mock_openai_response(content: str):
    """Build a minimal mock OpenAI response object."""
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    response = MagicMock()
    response.choices = [choice]
    return response


VALID_JSON = json.dumps({
    "mode": "C",
    "agencies_in_scope": ["RCW", "WAC", "SMC"],
    "agency_relevance": {"RCW": 3, "WAC": 2, "SMC": 2},
    "top_k": 24,
    "requires_numerical_comparison": False,
})


class TestAnalyzeQuery:
    def test_valid_json_response(self):
        """Returns AnalysisResult when LLM returns valid JSON."""
        mock_resp = _mock_openai_response(VALID_JSON)
        with patch("src.core.analyzer.OpenAI") as MockOpenAI:
            MockOpenAI.return_value.chat.completions.create.return_value = mock_resp
            result = analyze_query("EV charging conflicts between WAC and SMC")

        assert isinstance(result, AnalysisResult)
        assert result.mode == "C"
        assert result.agencies_in_scope == ["RCW", "WAC", "SMC"]
        assert result.agency_relevance["RCW"] == 3
        assert result.top_k == 24
        assert result.requires_numerical_comparison is False

    def test_strips_markdown_fences(self):
        """Handles ```json fences around the JSON."""
        fenced = f"```json\n{VALID_JSON}\n```"
        mock_resp = _mock_openai_response(fenced)
        with patch("src.core.analyzer.OpenAI") as MockOpenAI:
            MockOpenAI.return_value.chat.completions.create.return_value = mock_resp
            result = analyze_query("any query")

        assert result.mode == "C"

    def test_fallback_on_malformed_json(self):
        """Returns mode-C fallback when LLM returns garbage."""
        mock_resp = _mock_openai_response("not json at all!!")
        with patch("src.core.analyzer.OpenAI") as MockOpenAI:
            MockOpenAI.return_value.chat.completions.create.return_value = mock_resp
            result = analyze_query("any query")

        assert result.mode == "C"
        assert result.top_k == 32
        assert len(result.agencies_in_scope) == 8
        assert all(v == 2 for v in result.agency_relevance.values())

    def test_fallback_on_api_exception(self):
        """Returns mode-C fallback when OpenAI raises."""
        with patch("src.core.analyzer.OpenAI") as MockOpenAI:
            MockOpenAI.return_value.chat.completions.create.side_effect = Exception("timeout")
            result = analyze_query("any query")

        assert result.mode == "C"
        assert result.top_k == 32
