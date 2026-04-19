import anthropic
from agents.streaming import stream_agent_turn
from tools.search import search, SEARCH_SCHEMA
from tools.file_reader import read_file, FILE_READER_SCHEMA
from tools.list_directory import list_directory, LIST_DIRECTORY_SCHEMA

_client = anthropic.Anthropic()

DECISION_SYSTEM = """You are a decision support specialist who knows the user personally.

Approach every decision in this order:
1. Use list_directory on 'knowledge-base/' to see what personal context is available
2. Use read_file to read relevant KB files (preferences, past decisions, lessons)
3. Use search to research both sides of the decision from the web
4. Produce a structured response in this exact format:

## Decision: <topic>

**Your context (from knowledge base):**
- <key personal preference or past decision that applies>

**Analysis:**

### Option A: <name>
Pros: ...
Cons: ...

### Option B: <name>
Pros: ...
Cons: ...

**Recommendation:** <option> — <one sentence grounded in their personal context>

**Sources:** <list web sources used>

Ground recommendations in the user's stated preferences and past decisions, not just generic best practices."""

DECISION_TOOLS = [SEARCH_SCHEMA, FILE_READER_SCHEMA, LIST_DIRECTORY_SCHEMA]

MAX_ITERATIONS = 10


def _dispatch(name: str, inputs: dict) -> str:
    if name == "search":
        return search(inputs["query"])
    if name == "read_file":
        return read_file(inputs["path"])
    if name == "list_directory":
        return list_directory(inputs["path"])
    return f"Unknown tool: {name}"


def decision_agent_node(state) -> dict:
    content = stream_agent_turn(
        _client,
        system=DECISION_SYSTEM,
        tools=DECISION_TOOLS,
        messages=state["messages"],
        label="decision",
    )
    new_message = {"role": "assistant", "content": content}
    return {
        "messages": state["messages"] + [new_message],
        "iterations": state["iterations"] + 1,
    }


def decision_tool_node(state) -> dict:
    last_message = state["messages"][-1]
    tool_results = []
    for block in last_message["content"]:
        if block.get("type") == "tool_use":
            result = _dispatch(block["name"], block["input"])
            print(f"\n[tool_result] {block['name']}", flush=True)
            print(f"{result}\n", flush=True)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block["id"],
                "content": result,
            })
    return {"messages": state["messages"] + [{"role": "user", "content": tool_results}]}


def decision_should_continue(state) -> str:
    if state["iterations"] >= MAX_ITERATIONS:
        return "end"
    last = state["messages"][-1]
    if last.get("role") != "assistant":
        return "end"
    for block in last.get("content", []):
        if isinstance(block, dict) and block.get("type") == "tool_use":
            return "decision_tools"
    return "end"
