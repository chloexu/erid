from unittest.mock import patch
from state import AgentState
from graph import build_graph


def _state(query: str = "test", route: str = "") -> AgentState:
    return {
        "messages": [{"role": "user", "content": query}],
        "query": query,
        "iterations": 0,
        "route": route,
        "answer": "",
    }


def test_build_graph_returns_compiled_graph():
    graph = build_graph()
    assert graph is not None


def test_build_graph_accepts_checkpointer():
    graph = build_graph(checkpointer=None)
    assert graph is not None


def test_graph_has_expected_nodes():
    graph = build_graph()
    node_names = set(graph.get_graph().nodes.keys())
    assert "supervisor" in node_names
    assert "researcher" in node_names
    assert "researcher_tools" in node_names
    assert "summarizer" in node_names
    assert "decision" in node_names
    assert "decision_tools" in node_names
