from unittest.mock import patch, MagicMock
from tools.search import search, SEARCH_SCHEMA
from tools.file_reader import read_file, FILE_READER_SCHEMA
from tools.list_directory import list_directory, LIST_DIRECTORY_SCHEMA


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


def test_read_file_returns_contents(tmp_path):
    f = tmp_path / "hello.txt"
    f.write_text("hello world")
    assert read_file(str(f)) == "hello world"


def test_read_file_missing_returns_error():
    result = read_file("/nonexistent/path/file.txt")
    assert "Error" in result
    assert "not found" in result.lower()


def test_read_file_too_large_returns_error(tmp_path):
    big = tmp_path / "big.txt"
    big.write_text("x" * (11 * 1024))
    result = read_file(str(big))
    assert "Error" in result
    assert "too large" in result.lower()


def test_file_reader_schema():
    assert FILE_READER_SCHEMA["name"] == "read_file"
    assert "path" in FILE_READER_SCHEMA["input_schema"]["properties"]
    assert "path" in FILE_READER_SCHEMA["input_schema"]["required"]


def test_list_directory_returns_entries(tmp_path):
    (tmp_path / "subdir").mkdir()
    (tmp_path / "file.txt").write_text("hello")
    result = list_directory(str(tmp_path))
    assert "subdir" in result
    assert "file.txt" in result


def test_list_directory_empty(tmp_path):
    result = list_directory(str(tmp_path))
    assert "(empty)" in result


def test_list_directory_missing_returns_error():
    result = list_directory("/nonexistent/path")
    assert "Error" in result
    assert "not found" in result.lower()


def test_list_directory_on_file_returns_error(tmp_path):
    f = tmp_path / "file.txt"
    f.write_text("hello")
    result = list_directory(str(f))
    assert "Error" in result
    assert "not a directory" in result.lower()


def test_list_directory_schema():
    assert LIST_DIRECTORY_SCHEMA["name"] == "list_directory"
    assert "path" in LIST_DIRECTORY_SCHEMA["input_schema"]["properties"]
    assert "path" in LIST_DIRECTORY_SCHEMA["input_schema"]["required"]
