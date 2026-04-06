from typing import TypedDict


class AgentState(TypedDict):
    messages: list[dict]   # Anthropic-format message dicts
    query: str
    iterations: int
