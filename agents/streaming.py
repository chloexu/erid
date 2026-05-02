import json
import time
from anthropic import Anthropic
from observability.tracer import NullTracer

MODEL = "claude-sonnet-4-6"


def stream_agent_turn(
    client: Anthropic,
    *,
    system: str,
    tools: list,
    messages: list,
    label: str = "agent",
    max_tokens: int = 4096,
    tracer=None,
) -> list[dict]:
    """Stream an LLM turn that may call tools. Prints tokens live.

    Returns assembled content blocks (same shape as messages.create response).
    """
    if tracer is None:
        tracer = NullTracer()

    print(f"\n[{label}] Thinking...", flush=True)
    current_tool: dict | None = None
    t_start = time.monotonic()

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

        final = stream.get_final_message()

    duration_ms = int((time.monotonic() - t_start) * 1000)
    tracer.record_llm_call(
        label=label,
        model=MODEL,
        input_tok=final.usage.input_tokens,
        output_tok=final.usage.output_tokens,
        duration_ms=duration_ms,
    )

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
    tracer=None,
) -> str:
    """Stream a text-only LLM turn (no tools). Prints tokens live. Returns final text."""
    if tracer is None:
        tracer = NullTracer()

    print(f"\n[{label}] Writing...", flush=True)
    t_start = time.monotonic()

    with client.messages.stream(
        model=MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=messages,
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)
        final = stream.get_final_message()

    duration_ms = int((time.monotonic() - t_start) * 1000)
    tracer.record_llm_call(
        label=label,
        model=MODEL,
        input_tok=final.usage.input_tokens,
        output_tok=final.usage.output_tokens,
        duration_ms=duration_ms,
    )

    print(flush=True)
    return final.content[0].text if final.content else ""
