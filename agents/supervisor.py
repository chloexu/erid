import anthropic

_client = anthropic.Anthropic()

CLARITY_SYSTEM = """You are a query analyst. Your only job is to decide if a query is clear enough to act on without clarification.

A query is AMBIGUOUS if any of these are true:
- The scope is unclear (e.g. "tell me about my projects" — which project? all of them?)
- A key term could mean two different things (e.g. "how does auth work" — web concepts or a specific codebase?)
- The intent is unclear (e.g. "FastAPI vs Django" — is this a decision to make or just information to gather?)
- Acting on a wrong assumption would waste significant research effort

A query is CLEAR if:
- There is only one reasonable interpretation
- Any ambiguity doesn't change what you'd research

Respond in exactly this format (two lines, nothing else):
Clear: <yes|no>
Question: <one focused clarifying question, or "none" if clear>"""

SUPERVISOR_SYSTEM = """Classify the user's query into exactly one of four categories.

Categories:
- research: requires searching the web for current information or external knowledge
- codebase: requires exploring or reading local project source code (e.g. how a feature is implemented, how auth works in a specific project)
- knowledge_base: requires reading the user's personal knowledge base (past decisions, lessons learned, preferences, project notes stored in knowledge-base/)
- decide: requires comparing options and making a recommendation (can use both web and personal knowledge)

Respond in exactly this format (two lines, nothing else):
Reasoning: <one sentence explaining your classification>
Route: <research|codebase|knowledge_base|decide>"""


MAX_CLARIFICATIONS = 2


def _check_clarity(client: anthropic.Anthropic, query: str) -> tuple[bool, str]:
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=100,
        system=CLARITY_SYSTEM,
        messages=[{"role": "user", "content": query}],
    )
    text = response.content[0].text if response.content else ""
    is_clear = True
    question = "none"
    for line in text.splitlines():
        if line.lower().startswith("clear:"):
            is_clear = line.split(":", 1)[1].strip().lower() == "yes"
        elif line.lower().startswith("question:"):
            question = line.split(":", 1)[1].strip()
    return is_clear, question


def supervisor_node(state) -> dict:
    query = state["query"]

    for _ in range(MAX_CLARIFICATIONS):
        is_clear, question = _check_clarity(_client, query)
        if is_clear or question == "none":
            break
        print(f"\n[supervisor] {question}", flush=True)
        answer = input("Your answer: ").strip()
        if not answer:
            break
        query += f"\n\nClarifying question: {question}\nAnswer: {answer}"

    print("\n[supervisor] Classifying query...", flush=True)

    with _client.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=100,
        system=SUPERVISOR_SYSTEM,
        messages=[{"role": "user", "content": query}],
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)
        final = stream.get_final_message()

    text = final.content[0].text if final.content else ""
    route = "research"
    for line in text.splitlines():
        if line.lower().startswith("route:"):
            extracted = line.split(":", 1)[1].strip().lower()
            if extracted in ("research", "codebase", "knowledge_base", "decide"):
                route = extracted
            break

    print(f"\n[routing -> {route}]\n", flush=True)
    return {
        "route": route,
        "query": query,
        "messages": [{"role": "user", "content": query}],
    }
