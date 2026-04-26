import anthropic
from agents.streaming import stream_agent_turn
from tools.search import search, SEARCH_SCHEMA
from tools.file_reader import read_file, FILE_READER_SCHEMA
from tools.list_directory import list_directory, LIST_DIRECTORY_SCHEMA

_client = anthropic.Anthropic()

RESEARCH_SYSTEM = (
    "You are a research specialist. Search the web and read files to gather information. "
    "Search multiple times if needed to get comprehensive coverage. "
    "When you have enough information, stop calling tools and summarize what you found."
)

CODEBASE_SYSTEM = (
    "You are a codebase explorer. Use list_directory to navigate the project structure, "
    "then read_file to examine relevant source files. "
    "When you have enough context to answer the question, stop calling tools and summarize what you found."
)

KB_SYSTEM = (
    "You are a personal knowledge base assistant. Use list_directory on 'knowledge-base/' to see what's available, "
    "then read_file to read relevant files (decisions, lessons, preferences, project notes). "
    "When you have read the relevant files, stop calling tools and summarize what you found."
)

RESEARCHER_TOOLS = [SEARCH_SCHEMA, FILE_READER_SCHEMA, LIST_DIRECTORY_SCHEMA]

MAX_ITERATIONS = 10


def _dispatch(name: str, inputs: dict) -> str:
    if name == "search":
        return search(inputs["query"])
    if name == "read_file":
        return read_file(inputs["path"])
    if name == "list_directory":
        return list_directory(inputs["path"])
    return f"Unknown tool: {name}"


def researcher_agent_node(state) -> dict:
    route = state.get("route")
    if route == "codebase":
        system = CODEBASE_SYSTEM
    elif route == "knowledge_base":
        system = KB_SYSTEM
    else:
        system = RESEARCH_SYSTEM
    content = stream_agent_turn(
        _client,
        system=system,
        tools=RESEARCHER_TOOLS,
        messages=state["messages"],
        label="researcher",
    )
    new_message = {"role": "assistant", "content": content}
    return {
        "messages": state["messages"] + [new_message],
        "iterations": state["iterations"] + 1,
    }


def researcher_tool_node(state) -> dict:
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


def researcher_should_continue(state) -> str:
    if state["iterations"] >= MAX_ITERATIONS:
        return "summarize"
    last = state["messages"][-1]
    if last.get("role") != "assistant":
        return "summarize"
    for block in last.get("content", []):
        if isinstance(block, dict) and block.get("type") == "tool_use":
            return "researcher_tools"
    return "summarize"
