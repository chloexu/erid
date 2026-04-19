import anthropic

_client = anthropic.Anthropic()

SUPERVISOR_SYSTEM = """Classify the user's query into exactly one of three categories.

Categories:
- research: requires searching the web for current information
- codebase: requires exploring or reading local files or codebases
- decide: requires comparing options and making a recommendation (can use both web and personal knowledge)

Respond in exactly this format (two lines, nothing else):
Reasoning: <one sentence explaining your classification>
Route: <research|codebase|decide>"""


def supervisor_node(state) -> dict:
    print("\n[supervisor] Classifying query...", flush=True)

    with _client.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=100,
        system=SUPERVISOR_SYSTEM,
        messages=[{"role": "user", "content": state["query"]}],
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)
        final = stream.get_final_message()

    text = final.content[0].text if final.content else ""
    route = "research"
    for line in text.splitlines():
        if line.lower().startswith("route:"):
            extracted = line.split(":", 1)[1].strip().lower()
            if extracted in ("research", "codebase", "decide"):
                route = extracted
            break

    print(f"\n[routing -> {route}]\n", flush=True)
    return {"route": route}
