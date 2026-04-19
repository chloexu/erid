import anthropic
from langgraph.graph import StateGraph, END
from state import AgentState
from tools.search import search, SEARCH_SCHEMA

_client = anthropic.Anthropic()

SYSTEM_PROMPT = (
    "You are a research assistant. Use the search tool to find information. "
    "When you have enough information to answer the question, stop calling tools and provide a final answer."
)

TOOLS_SCHEMA = [SEARCH_SCHEMA]

MAX_ITERATIONS = 10


def agent_node(state: AgentState) -> dict:
    import json
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
                    try:
                        current_tool["input"] = json.loads(current_tool["input"])
                    except (json.JSONDecodeError, TypeError):
                        pass
                    print(f"  input: {current_tool['input']}", flush=True)
                    content.append(current_tool)
                    current_tool = None

        final = stream.get_final_message()
        for block in final.content:
            if block.type == "text" and not any(b.get("type") == "text" for b in content):
                content.append({"type": "text", "text": block.text})

    print(flush=True)
    new_message = {"role": "assistant", "content": content}
    return {
        "messages": state["messages"] + [new_message],
        "iterations": state["iterations"] + 1,
    }


def tool_node(state: AgentState) -> dict:
    last_message = state["messages"][-1]
    tool_results = []
    for block in last_message["content"]:
        if block.get("type") == "tool_use":
            result = dispatch_tool(block["name"], block["input"])
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block["id"],
                "content": result,
            })
    tool_message = {"role": "user", "content": tool_results}
    return {"messages": state["messages"] + [tool_message]}


def dispatch_tool(name: str, inputs: dict) -> str:
    if name == "search":
        return search(inputs["query"])
    return f"Unknown tool: {name}"


def should_continue(state: AgentState) -> str:
    if state["iterations"] >= MAX_ITERATIONS:
        return "end"
    last_message = state["messages"][-1]
    if last_message.get("role") != "assistant":
        return "end"
    for block in last_message.get("content", []):
        if isinstance(block, dict) and block.get("type") == "tool_use":
            return "tools"
    return "end"


def build_graph(checkpointer=None):
    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)
    graph.set_entry_point("agent")
    graph.add_conditional_edges(
        "agent",
        should_continue,
        {"tools": "tools", "end": END},
    )
    graph.add_edge("tools", "agent")
    return graph.compile(checkpointer=checkpointer)
