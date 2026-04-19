from unittest.mock import MagicMock, patch
from state import AgentState
from graph import should_continue, dispatch_tool, build_graph, agent_node


def _make_state(content: list, iterations: int = 0) -> AgentState:
    return {
        "messages": [{"role": "assistant", "content": content}],
        "query": "test",
        "iterations": iterations,
    }


def test_should_continue_returns_tools_when_tool_use_block():
    state = _make_state([{"type": "tool_use", "id": "x", "name": "search", "input": {"query": "q"}}])
    assert should_continue(state) == "tools"


def test_should_continue_returns_end_when_text_only():
    state = _make_state([{"type": "text", "text": "Here is my answer."}])
    assert should_continue(state) == "end"


def test_should_continue_returns_end_when_max_iterations():
    state = _make_state(
        [{"type": "tool_use", "id": "x", "name": "search", "input": {"query": "q"}}],
        iterations=10,
    )
    assert should_continue(state) == "end"


def test_dispatch_tool_unknown_returns_error():
    result = dispatch_tool("nonexistent_tool", {})
    assert "Unknown tool" in result


def test_build_graph_returns_compiled_graph():
    graph = build_graph()
    assert graph is not None


def test_agent_node_streaming_returns_correct_shape():
    mock_stream = MagicMock()
    mock_stream.__enter__ = MagicMock(return_value=mock_stream)
    mock_stream.__exit__ = MagicMock(return_value=False)
    mock_stream.__iter__ = MagicMock(return_value=iter([]))
    final_msg = MagicMock()
    final_msg.content = [MagicMock(type="text", text="LangGraph is a framework.")]
    mock_stream.get_final_message = MagicMock(return_value=final_msg)

    with patch("graph._client") as mock_client:
        mock_client.messages.stream.return_value = mock_stream
        state = {
            "messages": [{"role": "user", "content": "What is LangGraph?"}],
            "query": "What is LangGraph?",
            "iterations": 0,
        }
        result = agent_node(state)

    assert "messages" in result
    assert result["iterations"] == 1
    last = result["messages"][-1]
    assert last["role"] == "assistant"
    assert isinstance(last["content"], list)
    assert any(b.get("type") == "text" for b in last["content"])
