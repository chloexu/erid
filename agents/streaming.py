import json
from anthropic import Anthropic

MODEL = "claude-sonnet-4-6"


def stream_agent_turn(
    client: Anthropic,
    *,
    system: str,
    tools: list,
    messages: list,
    label: str = "agent",
    max_tokens: int = 4096,
) -> list[dict]:
    """Stream an LLM turn that may call tools. Prints tokens live.

    Returns assembled content blocks (same shape as messages.create response).
    """
    print(f"\n[{label}] Thinking...", flush=True)
    current_tool: dict | None = None

    with client.messages.stream(
        model=MODEL,
        max_tokens=max_tokens,
        system=system,
        tools=tools,
        messages=messages,
    ) as stream:
        for event in stream:
            etype = type(event).__name__

            if etype == "RawContentBlockStartEvent":
                block = event.content_block
                if block.type == "tool_use":
                    current_tool = {
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": "",
                    }
                    print(f"\n[tool_use] {block.name}", flush=True)

            elif etype == "RawContentBlockDeltaEvent":
                delta = event.delta
                if delta.type == "text_delta":
                    print(delta.text, end="", flush=True)
                elif delta.type == "input_json_delta" and current_tool:
                    current_tool["input"] += delta.partial_json

            elif etype in ("RawContentBlockStopEvent", "ParsedContentBlockStopEvent"):
                if current_tool:
                    try:
                        current_tool["input"] = json.loads(current_tool["input"])
                    except (json.JSONDecodeError, TypeError):
                        pass
                    print(f"  input: {current_tool['input']}", flush=True)
                    current_tool = None

        # Use get_final_message() as authoritative source — more reliable than event accumulation
        final = stream.get_final_message()

    print(flush=True)
    content = []
    for block in final.content:
        if block.type == "text":
            content.append({"type": "text", "text": block.text})
        elif block.type == "tool_use":
            content.append({
                "type": "tool_use",
                "id": block.id,
                "name": block.name,
                "input": block.input,
            })
    return content


def stream_text_turn(
    client: Anthropic,
    *,
    system: str,
    messages: list,
    label: str,
    max_tokens: int = 2048,
) -> str:
    """Stream a text-only LLM turn (no tools). Prints tokens live. Returns final text."""
    print(f"\n[{label}] Writing...", flush=True)
    with client.messages.stream(
        model=MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=messages,
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)
        final = stream.get_final_message()
    print(flush=True)
    return final.content[0].text if final.content else ""
