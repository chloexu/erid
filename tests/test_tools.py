from unittest.mock import patch, MagicMock
from tools.search import search, SEARCH_SCHEMA


def test_search_returns_formatted_string():
    mock_results = {
        "results": [
            {"title": "LangGraph Docs", "url": "https://example.com/1", "content": "LangGraph is a framework."},
            {"title": "LangGraph Tutorial", "url": "https://example.com/2", "content": "Build agents with LangGraph."},
        ]
    }
    with patch("tools.search.TavilyClient") as MockClient:
        mock_instance = MockClient.return_value
        mock_instance.search.return_value = mock_results
        result = search("LangGraph tutorial")

    assert "LangGraph Docs" in result
    assert "https://example.com/1" in result
    assert "LangGraph is a framework." in result
    assert "---" in result  # separator between results


def test_search_schema_has_required_fields():
    assert SEARCH_SCHEMA["name"] == "search"
    assert "query" in SEARCH_SCHEMA["input_schema"]["properties"]
    assert "query" in SEARCH_SCHEMA["input_schema"]["required"]
