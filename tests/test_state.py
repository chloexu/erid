from state import AgentState


def test_agent_state_has_required_fields():
    state: AgentState = {
        "messages": [],
        "query": "What is LangGraph?",
        "iterations": 0,
    }
    assert state["messages"] == []
    assert state["query"] == "What is LangGraph?"
    assert state["iterations"] == 0


def test_agent_state_messages_is_list_of_dicts():
    state: AgentState = {
        "messages": [{"role": "user", "content": "Hello"}],
        "query": "Hello",
        "iterations": 0,
    }
    assert isinstance(state["messages"][0], dict)
    assert state["messages"][0]["role"] == "user"
