from typing import TypedDict


class AgentState(TypedDict):
    messages: list[dict]   # Anthropic-format message dicts
    query: str
    iterations: int
    route: str             # set by supervisor: "research" | "codebase" | "decide"
    answer: str            # set by summarizer or decision node
