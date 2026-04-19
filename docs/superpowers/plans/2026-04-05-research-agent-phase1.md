# Research Agent — Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire a ReAct loop using LangGraph's StateGraph with Anthropic SDK called directly (no LangChain). Add real-time verbose streaming so every step of the agent loop is visible as it happens.

**Tech Stack:** Python 3.11+, LangGraph, Anthropic SDK, Tavily (web search), python-dotenv, pytest

**Design specs:**
- `docs/superpowers/specs/2026-04-05-research-agent-design.md` — original loop design
- `docs/superpowers/specs/2026-04-19-phase1-streaming-design.md` — streaming + verbose output

---

## File Map

```
research-agent/
├── main.py              # CLI entrypoint
├── graph.py             # StateGraph definition
├── state.py             # AgentState TypedDict
├── tools/
│   ├── __init__.py
│   └── search.py        # Tavily web search
├── tests/
│   ├── __init__.py
│   ├── test_state.py
│   ├── test_tools.py
│   └── test_graph.py
├── .env.example
├── .gitignore
├── pytest.ini
└── requirements.txt
```

---

## Status

- [x] Task 1: Project setup
- [x] Task 2: State schema
- [x] Task 3: Web search tool
- [x] Task 4: Agent node, tool node, and graph
- [x] Task 5: CLI entrypoint
- [ ] Task 6: Streaming + verbose output

---

## Task 1: Project Setup ✓

Completed. Files: `requirements.txt`, `.env.example`, `.gitignore`, `pytest.ini`, package init files.

---

## Task 2: State Schema ✓

Completed. `state.py` — `AgentState` TypedDict with `messages`, `query`, `iterations`.

---

## Task 3: Web Search Tool ✓

Completed. `tools/search.py` — Tavily-backed `search(query)` returning formatted string. `SEARCH_SCHEMA` for Anthropic tool use.

---

## Task 4: Agent Node, Tool Node, and Graph ✓

Completed. `graph.py` — `agent_node`, `tool_node`, `dispatch_tool`, `should_continue`, `build_graph`.

---

## Task 5: CLI Entrypoint ✓

Completed. `main.py` — `run(query)` using `graph.invoke()`, prints final answer.

---

## Task 6: Streaming + Verbose Output

**Design:** `docs/superpowers/specs/2026-04-19-phase1-streaming-design.md`

**Files:**
- Modify: `graph.py`
- Modify: `main.py`
- Modify: `tests/test_graph.py`

**Target output:**
```
Query: What is LangGraph?

Thinking...
[reasoning tokens stream live...]

[tool_use] search
  input: {"query": "LangGraph framework"}

[tool_result] search
  LangGraph is a library for...
  [full raw Tavily result]

Thinking...
[final answer streams live...]
```

---

### Step 1: Write failing test for streaming agent_node

Append to `tests/test_graph.py`:

```python
from unittest.mock import patch, MagicMock

def test_agent_node_streaming_returns_correct_shape():
    """agent_node must return same state shape whether streaming or not."""
    mock_stream = MagicMock()
    mock_stream.__enter__ = MagicMock(return_value=mock_stream)
    mock_stream.__exit__ = MagicMock(return_value=False)
    mock_stream.text_stream = iter(["LangGraph ", "is a ", "framework."])
    mock_stream.get_final_message = MagicMock(return_value=MagicMock(
        content=[MagicMock(type="text", text="LangGraph is a framework.")],
        stop_reason="end_turn",
    ))

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
```

Run:
```bash
pytest tests/test_graph.py::test_agent_node_streaming_returns_correct_shape -v
```
Expected: FAIL (agent_node still uses `messages.create`)

---

### Step 2: Update graph.py — switch agent_node to streaming

Replace `agent_node` in `graph.py`:

```python
def agent_node(state: AgentState) -> dict:
    print("\nThinking...", flush=True)
    content = []
    current_tool: dict | None = None

    with _client.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        tools=TOOLS_SCHEMA,
        messages=state["messages"],
    ) as stream:
        for event in stream:
            event_type = type(event).__name__

            if event_type == "RawContentBlockStartEvent":
                block = event.content_block
                if block.type == "tool_use":
                    current_tool = {"type": "tool_use", "id": block.id, "name": block.name, "input": ""}
                    print(f"\n[tool_use] {block.name}", flush=True)

            elif event_type == "RawContentBlockDeltaEvent":
                delta = event.delta
                if delta.type == "text_delta":
                    print(delta.text, end="", flush=True)
                elif delta.type == "input_json_delta" and current_tool:
                    current_tool["input"] += delta.partial_json

            elif event_type == "RawContentBlockStopEvent":
                if current_tool:
                    import json
                    try:
                        current_tool["input"] = json.loads(current_tool["input"])
                    except (json.JSONDecodeError, TypeError):
                        pass
                    print(f"  input: {current_tool['input']}", flush=True)
                    content.append(current_tool)
                    current_tool = None

        # Collect any text blocks from the final message
        final = stream.get_final_message()
        for block in final.content:
            if block.type == "text" and not any(
                b.get("type") == "text" for b in content
            ):
                content.append({"type": "text", "text": block.text})

    print(flush=True)
    new_message = {"role": "assistant", "content": content}
    return {
        "messages": state["messages"] + [new_message],
        "iterations": state["iterations"] + 1,
    }
```

Run:
```bash
pytest tests/test_graph.py -v
```
Expected: all PASSED

---

### Step 3: Update main.py — switch to graph.stream(), print tool results

Replace `run()` and `__main__` block in `main.py`:

```python
import sys
from dotenv import load_dotenv
from graph import build_graph
from state import AgentState

load_dotenv()


def run(query: str) -> None:
    graph = build_graph()
    initial_state: AgentState = {
        "messages": [{"role": "user", "content": query}],
        "query": query,
        "iterations": 0,
    }

    for event in graph.stream(initial_state, stream_mode="updates"):
        if "tools" in event:
            tools_state = event["tools"]
            last_message = tools_state["messages"][-1]
            for block in last_message.get("content", []):
                if block.get("type") == "tool_result":
                    # Find the tool name from prior assistant message
                    tool_name = block.get("tool_use_id", "tool")
                    print(f"\n[tool_result] {tool_name}", flush=True)
                    print(f"  {block.get('content', '')}\n", flush=True)


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) or "What is LangGraph and how does it work?"
    print(f"\nQuery: {query}\n")
    run(query)
    print()
```

---

### Step 4: Manual smoke test

```bash
python main.py "What is LangGraph and what problems does it solve?"
```

Expected:
- `Thinking...` prints immediately
- Reasoning tokens stream live
- `[tool_use] search` + input prints when tool fires
- `[tool_result] search` + full Tavily result prints
- `Thinking...` again for final synthesis
- Final answer streams word-by-word

---

### Step 5: Run full test suite

```bash
pytest -v
```

Expected: all PASSED

---

### Step 6: Commit

```bash
git add graph.py main.py tests/test_graph.py
git commit -m "feat: add streaming + verbose output — phase 1 complete"
```
