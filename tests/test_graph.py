from state import AgentState
from graph import should_continue, dispatch_tool, build_graph


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
