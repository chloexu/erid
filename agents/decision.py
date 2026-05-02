import anthropic
import time
from agents.streaming import stream_agent_turn
from observability import get_tracer
from tools.search import search, SEARCH_SCHEMA
from tools.file_reader import read_file, FILE_READER_SCHEMA
from tools.list_directory import list_directory, LIST_DIRECTORY_SCHEMA

_client = anthropic.Anthropic()

FRAMING_SYSTEM = """Extract the decision framing from the user's query in exactly this format (two lines, nothing else):
Deciding: <what is being compared or decided, e.g. "FastAPI vs Django">
Goal: <what they're trying to achieve, one short phrase>"""

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


def _format_tool_sources(name: str, inputs: dict, result: str) -> str:
    if name == "search":
        sources = []
        for line in result.splitlines():
            line = line.strip()
            if line.startswith("http://") or line.startswith("https://"):
                sources.append(line)
        return "  sources: " + ", ".join(sources) if sources else ""
    if name == "read_file":
        return f"  file: {inputs.get('path', '')}"
    if name == "list_directory":
        return f"  dir: {inputs.get('path', '')}"
    return ""


def _check_file_access(path: str, route: str) -> str | None:
    """Returns a warning message if the path needs user confirmation, else None."""
    if path.startswith("/") or path.startswith("~"):
        return f"absolute path outside project: {path}"
    if ".." in path:
        return f"path traversal detected: {path}"
    if route == "knowledge_base" and not path.startswith("knowledge-base/"):
        return f"outside knowledge-base/: {path}"
    return None


def decision_framing_node(state) -> dict:
    query = state["query"]
    response = _client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=100,
        system=FRAMING_SYSTEM,
        messages=[{"role": "user", "content": query}],
    )
    framing = response.content[0].text.strip() if response.content else ""
    print(f"\n[decision framing]\n{framing}", flush=True)
    correction = input("\nCorrect? Press enter to proceed, or type a correction: ").strip()
    if correction:
        updated_query = query + f"\n\nFraming correction: {correction}"
        return {
            "query": updated_query,
            "messages": [{"role": "user", "content": updated_query}],
        }
    return {}


def _dispatch(name: str, inputs: dict) -> str:
    if name == "search":
        return search(inputs["query"])
    if name == "read_file":
        return read_file(inputs["path"])
    if name == "list_directory":
        return list_directory(inputs["path"])
    return f"Unknown tool: {name}"


def decision_agent_node(state) -> dict:
    tracer = get_tracer()
    tracer.record_node_start("decision")
    content = stream_agent_turn(
        _client,
        system=DECISION_SYSTEM,
        tools=DECISION_TOOLS,
        messages=state["messages"],
        label="decision",
        tracer=tracer,
    )
    new_message = {"role": "assistant", "content": content}
    update = {
        "messages": state["messages"] + [new_message],
        "iterations": state["iterations"] + 1,
    }
    # Check if this is a final turn (no tool calls)
    is_final = not any(
        isinstance(block, dict) and block.get("type") == "tool_use"
        for block in content
    )
    if is_final:
        answer_text = " ".join(
            block.get("text", "") for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        )
        update["answer"] = answer_text
    return update


def decision_tool_node(state) -> dict:
    tracer = get_tracer()
    last_message = state["messages"][-1]
    route = state.get("route", "")
    tool_results = []
    for block in last_message["content"]:
        if block.get("type") == "tool_use":
            name = block["name"]
            inputs = block["input"]
            if name in ("read_file", "list_directory"):
                warning = _check_file_access(inputs.get("path", ""), route)
                if warning:
                    print(f"\n[file_access] {warning}", flush=True)
                    answer = input("Allow? (y/n): ").strip().lower()
                    if answer != "y":
                        tracer.record_tool_call(name=name, tool_input=inputs, duration_ms=0, denied=True)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block["id"],
                            "content": "Access denied by user.",
                        })
                        continue
            t_start = time.monotonic()
            result = _dispatch(name, inputs)
            duration_ms = int((time.monotonic() - t_start) * 1000)
            tracer.record_tool_call(name=name, tool_input=inputs, duration_ms=duration_ms, denied=False)
            print(f"\n[tool_result] {name}", flush=True)
            sources_line = _format_tool_sources(name, inputs, result)
            if sources_line:
                print(sources_line, flush=True)
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
