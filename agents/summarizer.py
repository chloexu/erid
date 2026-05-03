import anthropic
from agents.streaming import stream_text_turn
from observability import get_tracer

_client = anthropic.Anthropic()

SUMMARIZER_SYSTEM = (
    "You are a synthesis specialist. You receive research gathered by a research agent. "
    "Produce a clear, concise answer to the original question. "
    "Cite sources as [Source: URL or title] inline. "
    "If the research comes from local files, cite the file path."
)


def summarizer_node(state) -> dict:
    tracer = get_tracer()
    tracer.record_node_start("summarizer")
    summary_prompt = (
        f"Original question: {state['query']}\n\n"
        "Based on the research above, provide a clear, cited answer."
    )
    messages = state["messages"] + [{"role": "user", "content": summary_prompt}]
    answer = stream_text_turn(
        _client,
        system=SUMMARIZER_SYSTEM,
        messages=messages,
        label="summarizer",
        model="claude-haiku-4-5-20251001",
        tracer=tracer,
    )
    return {"answer": answer}
