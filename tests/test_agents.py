from unittest.mock import MagicMock, patch
from state import AgentState


def _base_state(query: str = "test query") -> AgentState:
    return {
        "messages": [{"role": "user", "content": query}],
        "query": query,
        "iterations": 0,
        "route": "",
        "answer": "",
    }


# ── Supervisor ─────────────────────────────────────────────────────────────────

from agents.supervisor import supervisor_node


def _mock_stream(text: str):
    mock = MagicMock()
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    mock.text_stream = iter([text])
    final_msg = MagicMock()
    final_msg.content = [MagicMock(text=text)]
    mock.get_final_message = MagicMock(return_value=final_msg)
    return mock


def test_supervisor_routes_research():
    text = "Reasoning: web lookup needed\nRoute: research"
    with patch("agents.supervisor._client") as mock_client:
        mock_client.messages.stream.return_value = _mock_stream(text)
        result = supervisor_node(_base_state("What is LangGraph?"))
    assert result["route"] == "research"


def test_supervisor_routes_codebase():
    text = "Reasoning: exploring local code\nRoute: codebase"
    with patch("agents.supervisor._client") as mock_client:
        mock_client.messages.stream.return_value = _mock_stream(text)
        result = supervisor_node(_base_state("How does auth work in chefs-hub?"))
    assert result["route"] == "codebase"


def test_supervisor_routes_decide():
    text = "Reasoning: decision needed\nRoute: decide"
    with patch("agents.supervisor._client") as mock_client:
        mock_client.messages.stream.return_value = _mock_stream(text)
        result = supervisor_node(_base_state("Should I use FastAPI or Django?"))
    assert result["route"] == "decide"


def test_supervisor_defaults_to_research_on_unknown_route():
    text = "Reasoning: unclear\nRoute: something_else"
    with patch("agents.supervisor._client") as mock_client:
        mock_client.messages.stream.return_value = _mock_stream(text)
        result = supervisor_node(_base_state("random query"))
    assert result["route"] == "research"
