import sys
from dotenv import load_dotenv

load_dotenv()  # must run before graph import — client is instantiated at module load time

from graph import build_graph
from state import AgentState


def run(query: str) -> None:
    graph = build_graph()
    initial_state: AgentState = {
        "messages": [{"role": "user", "content": query}],
        "query": query,
        "iterations": 0,
        "route": "",
        "answer": "",
    }
    # All streaming output (supervisor, researcher, decision, summarizer) prints directly to stdout.
    # We just need to drive the graph to completion.
    for _ in graph.stream(initial_state, stream_mode="updates"):
        pass

    print()  # trailing newline after streamed output


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) or "What is LangGraph and how does it work?"
    print(f"\nQuery: {query}\n")
    run(query)
