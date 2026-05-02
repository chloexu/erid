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
    with patch("agents.supervisor._check_clarity", return_value=(True, "none")):
        with patch("agents.supervisor._client") as mock_client:
            mock_client.messages.stream.return_value = _mock_stream(text)
            result = supervisor_node(_base_state("What is LangGraph?"))
    assert result["route"] == "research"


def test_supervisor_routes_codebase():
    text = "Reasoning: exploring local code\nRoute: codebase"
    with patch("agents.supervisor._check_clarity", return_value=(True, "none")):
        with patch("agents.supervisor._client") as mock_client:
            mock_client.messages.stream.return_value = _mock_stream(text)
            result = supervisor_node(_base_state("How does auth work in chefs-hub?"))
    assert result["route"] == "codebase"


def test_supervisor_routes_decide():
    text = "Reasoning: decision needed\nRoute: decide"
    with patch("agents.supervisor._check_clarity", return_value=(True, "none")):
        with patch("agents.supervisor._client") as mock_client:
            mock_client.messages.stream.return_value = _mock_stream(text)
            result = supervisor_node(_base_state("Should I use FastAPI or Django?"))
    assert result["route"] == "decide"


def test_supervisor_routes_knowledge_base():
    text = "Reasoning: querying personal KB\nRoute: knowledge_base"
    with patch("agents.supervisor._check_clarity", return_value=(True, "none")):
        with patch("agents.supervisor._client") as mock_client:
            mock_client.messages.stream.return_value = _mock_stream(text)
            result = supervisor_node(_base_state("What lessons have I learned about microservices?"))
    assert result["route"] == "knowledge_base"


def test_supervisor_defaults_to_research_on_unknown_route():
    text = "Reasoning: unclear\nRoute: something_else"
    with patch("agents.supervisor._check_clarity", return_value=(True, "none")):
        with patch("agents.supervisor._client") as mock_client:
            mock_client.messages.stream.return_value = _mock_stream(text)
            result = supervisor_node(_base_state("random query"))
    assert result["route"] == "research"


def test_supervisor_asks_clarification_when_ambiguous():
    text = "Reasoning: exploring local code\nRoute: codebase"
    with patch("agents.supervisor._check_clarity", side_effect=[(False, "Which project?"), (True, "none")]):
        with patch("agents.supervisor._client") as mock_client:
            mock_client.messages.stream.return_value = _mock_stream(text)
            with patch("builtins.input", return_value="chefs-hub"):
                result = supervisor_node(_base_state("how does auth work?"))
    assert result["route"] == "codebase"
    assert "Clarifying question: Which project?" in result["query"]
    assert "Answer: chefs-hub" in result["query"]


def test_supervisor_enriched_query_passed_to_messages():
    text = "Reasoning: exploring local code\nRoute: codebase"
    with patch("agents.supervisor._check_clarity", side_effect=[(False, "Which project?"), (True, "none")]):
        with patch("agents.supervisor._client") as mock_client:
            mock_client.messages.stream.return_value = _mock_stream(text)
            with patch("builtins.input", return_value="chefs-hub"):
                result = supervisor_node(_base_state("how does auth work?"))
    assert result["messages"] == [{"role": "user", "content": result["query"]}]


def test_supervisor_proceeds_after_max_clarifications():
    text = "Reasoning: web lookup needed\nRoute: research"
    with patch("agents.supervisor._check_clarity", return_value=(False, "Be more specific?")):
        with patch("agents.supervisor._client") as mock_client:
            mock_client.messages.stream.return_value = _mock_stream(text)
            with patch("builtins.input", return_value="still vague"):
                result = supervisor_node(_base_state("explain things"))
    assert result["route"] == "research"
    assert result["query"].count("Clarifying question:") == 2


def test_supervisor_records_clarification():
    """Verify that clarification questions are recorded via tracer."""
    with patch("agents.supervisor._check_clarity", side_effect=[(False, "Which project?"), (True, "none")]):
        with patch("agents.supervisor._client") as mock_client:
            text = "Reasoning: exploring local code\nRoute: codebase"
            mock_client.messages.stream.return_value = _mock_stream(text)
            with patch("builtins.input", return_value="chefs-hub"):
                with patch("agents.supervisor.get_tracer") as mock_get_tracer:
                    mock_tracer = MagicMock()
                    mock_get_tracer.return_value = mock_tracer
                    result = supervisor_node(_base_state("how does auth work?"))

    # Verify record_clarification was called with the question and answer
    mock_tracer.record_clarification.assert_called_once_with("Which project?", "chefs-hub")


def test_supervisor_records_routing():
    """Verify that routing is recorded via tracer with reasoning."""
    text = "Reasoning: exploring local code\nRoute: codebase"
    with patch("agents.supervisor._check_clarity", return_value=(True, "none")):
        with patch("agents.supervisor._client") as mock_client:
            mock_client.messages.stream.return_value = _mock_stream(text)
            with patch("agents.supervisor.get_tracer") as mock_get_tracer:
                mock_tracer = MagicMock()
                mock_get_tracer.return_value = mock_tracer
                result = supervisor_node(_base_state("How does auth work in chefs-hub?"))

    # Verify record_routing was called with route and the full text as reasoning
    mock_tracer.record_routing.assert_called_once()
    call_args = mock_tracer.record_routing.call_args
    assert call_args[0][0] == "codebase"  # route
    assert "exploring local code" in call_args[0][1]  # reasoning contains the text


# ── Researcher ─────────────────────────────────────────────────────────────────

from agents.researcher import researcher_agent_node, researcher_tool_node, researcher_should_continue


def _research_state(query: str = "What is LangGraph?", route: str = "research") -> AgentState:
    return {
        "messages": [{"role": "user", "content": query}],
        "query": query,
        "iterations": 0,
        "route": route,
        "answer": "",
    }


def test_researcher_agent_node_returns_updated_messages():
    with patch("agents.researcher.stream_agent_turn", return_value=[{"type": "text", "text": "Done."}]):
        state = _research_state()
        result = researcher_agent_node(state)
    assert len(result["messages"]) == len(state["messages"]) + 1
    assert result["messages"][-1]["role"] == "assistant"
    assert result["iterations"] == 1


def test_researcher_agent_node_codebase_route():
    with patch("agents.researcher.stream_agent_turn", return_value=[{"type": "text", "text": "Found it."}]):
        state = _research_state(query="How does auth work?", route="codebase")
        result = researcher_agent_node(state)
    assert result["iterations"] == 1


def test_researcher_agent_node_knowledge_base_route():
    with patch("agents.researcher.stream_agent_turn", return_value=[{"type": "text", "text": "Your lessons say..."}]):
        state = _research_state(query="What lessons have I learned?", route="knowledge_base")
        result = researcher_agent_node(state)
    assert result["iterations"] == 1


def test_researcher_should_continue_tools():
    state = _research_state()
    state["messages"].append({
        "role": "assistant",
        "content": [{"type": "tool_use", "id": "x", "name": "search", "input": {}}],
    })
    assert researcher_should_continue(state) == "researcher_tools"


def test_researcher_should_continue_summarize():
    state = _research_state()
    state["messages"].append({
        "role": "assistant",
        "content": [{"type": "text", "text": "Here is what I found."}],
    })
    assert researcher_should_continue(state) == "summarize"


def test_researcher_should_continue_max_iterations():
    state = _research_state()
    state["iterations"] = 10
    state["messages"].append({
        "role": "assistant",
        "content": [{"type": "tool_use", "id": "x", "name": "search", "input": {}}],
    })
    assert researcher_should_continue(state) == "summarize"


def test_researcher_tool_node_executes_search():
    state = _research_state()
    state["messages"].append({
        "role": "assistant",
        "content": [{"type": "tool_use", "id": "tu_1", "name": "search", "input": {"query": "LangGraph"}}],
    })
    with patch("agents.researcher.search", return_value="Search results here"):
        result = researcher_tool_node(state)
    last = result["messages"][-1]
    assert last["role"] == "user"
    assert last["content"][0]["type"] == "tool_result"
    assert last["content"][0]["content"] == "Search results here"


# ── Summarizer ─────────────────────────────────────────────────────────────────

from agents.summarizer import summarizer_node


def _summarizer_state(research_text: str) -> AgentState:
    return {
        "messages": [
            {"role": "user", "content": "What is LangGraph?"},
            {"role": "assistant", "content": [{"type": "text", "text": research_text}]},
        ],
        "query": "What is LangGraph?",
        "iterations": 1,
        "route": "research",
        "answer": "",
    }


def test_summarizer_returns_answer():
    with patch("agents.summarizer.stream_text_turn", return_value="LangGraph is a framework. [Source: example.com]"):
        result = summarizer_node(_summarizer_state("LangGraph is a state graph library."))
    assert result["answer"] == "LangGraph is a framework. [Source: example.com]"


def test_summarizer_answer_is_string():
    with patch("agents.summarizer.stream_text_turn", return_value="Some answer."):
        result = summarizer_node(_summarizer_state("context"))
    assert isinstance(result["answer"], str)


# ── Decision ───────────────────────────────────────────────────────────────────

from agents.decision import decision_agent_node, decision_tool_node, decision_should_continue


def _decision_state(query: str = "FastAPI vs Django?") -> AgentState:
    return {
        "messages": [{"role": "user", "content": query}],
        "query": query,
        "iterations": 0,
        "route": "decide",
        "answer": "",
    }


def test_decision_agent_node_returns_updated_messages():
    with patch("agents.decision.stream_agent_turn", return_value=[{"type": "text", "text": "## Decision\nUse FastAPI."}]):
        result = decision_agent_node(_decision_state())
    assert len(result["messages"]) == 2
    assert result["messages"][-1]["role"] == "assistant"
    assert result["iterations"] == 1


def test_decision_should_continue_tools():
    state = _decision_state()
    state["messages"].append({
        "role": "assistant",
        "content": [{"type": "tool_use", "id": "x", "name": "read_file", "input": {"path": "kb/prefs.md"}}],
    })
    assert decision_should_continue(state) == "decision_tools"


def test_decision_should_continue_end_on_text():
    state = _decision_state()
    state["messages"].append({
        "role": "assistant",
        "content": [{"type": "text", "text": "## Decision\nUse FastAPI."}],
    })
    assert decision_should_continue(state) == "end"


def test_decision_should_continue_end_on_max_iterations():
    state = _decision_state()
    state["iterations"] = 10
    state["messages"].append({
        "role": "assistant",
        "content": [{"type": "tool_use", "id": "x", "name": "search", "input": {}}],
    })
    assert decision_should_continue(state) == "end"


def test_decision_tool_node_executes_read_file():
    state = _decision_state()
    state["messages"].append({
        "role": "assistant",
        "content": [{"type": "tool_use", "id": "tu_1", "name": "read_file", "input": {"path": "kb/prefs.md"}}],
    })
    with patch("agents.decision.read_file", return_value="Prefer FastAPI."):
        result = decision_tool_node(state)
    last = result["messages"][-1]
    assert last["content"][0]["content"] == "Prefer FastAPI."


# ── Streaming tracer instrumentation ────────────────────────────────────────

from agents.streaming import stream_agent_turn, stream_text_turn


def _mock_agent_stream(text="result", input_tokens=500, output_tokens=100):
    mock = MagicMock()
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    mock.__iter__ = MagicMock(return_value=iter([]))
    final = MagicMock()
    final.content = [MagicMock(type="text", text=text, id=None)]
    final.usage.input_tokens = input_tokens
    final.usage.output_tokens = output_tokens
    mock.get_final_message = MagicMock(return_value=final)
    return mock


def _mock_text_stream(text="result", input_tokens=200, output_tokens=80):
    mock = MagicMock()
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    mock.text_stream = iter([text])
    final = MagicMock()
    final.content = [MagicMock(text=text)]
    final.usage.input_tokens = input_tokens
    final.usage.output_tokens = output_tokens
    mock.get_final_message = MagicMock(return_value=final)
    return mock


def test_stream_agent_turn_calls_record_llm_call():
    tracer = MagicMock()
    client = MagicMock()
    client.messages.stream.return_value = _mock_agent_stream(input_tokens=500, output_tokens=100)

    stream_agent_turn(
        client,
        system="sys",
        tools=[],
        messages=[],
        label="researcher",
        tracer=tracer,
    )

    tracer.record_llm_call.assert_called_once()
    args, kwargs = tracer.record_llm_call.call_args
    all_args = list(args) + list(kwargs.values())
    assert "researcher" in all_args
    assert 500 in all_args
    assert 100 in all_args


def test_stream_text_turn_calls_record_llm_call():
    tracer = MagicMock()
    client = MagicMock()
    client.messages.stream.return_value = _mock_text_stream(input_tokens=200, output_tokens=80)

    stream_text_turn(
        client,
        system="sys",
        messages=[],
        label="summarizer",
        tracer=tracer,
    )

    tracer.record_llm_call.assert_called_once()
    args, kwargs = tracer.record_llm_call.call_args
    all_args = list(args) + list(kwargs.values())
    assert "summarizer" in all_args
    assert 200 in all_args
    assert 80 in all_args


def test_stream_agent_turn_no_tracer_does_not_crash():
    client = MagicMock()
    client.messages.stream.return_value = _mock_agent_stream()
    # No tracer passed — should use NullTracer internally, no error
    stream_agent_turn(client, system="sys", tools=[], messages=[], label="test")
