import argparse
import sys
import time
import uuid
from dotenv import load_dotenv

load_dotenv()  # must run before graph import — client is instantiated at module load time

from graph import build_graph
from observability import get_tracer, set_tracer
from observability.inspect import inspect_run
from observability.tracer import DB_PATH, Tracer
from state import AgentState


def run(query: str) -> None:
    set_tracer(Tracer())
    tracer = get_tracer()
    run_id = str(uuid.uuid4())[:8]
    tracer.start_run(run_id, query)

    t_start = time.monotonic()

    graph = build_graph()
    initial_state: AgentState = {
        "messages": [{"role": "user", "content": query}],
        "query": query,
        "iterations": 0,
        "route": "",
        "answer": "",
    }

    # stream_mode="values" yields full state snapshots — needed to extract final answer
    final_state = None
    for state in graph.stream(initial_state, stream_mode="values"):
        final_state = state

    print()  # trailing newline after streamed output

    duration_ms = int((time.monotonic() - t_start) * 1000)
    answer = final_state.get("answer", "") if final_state else ""
    tracer.finish_run(answer, duration_ms)
    print(f"\nRun ID: {run_id}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Erid AI assistant")
    parser.add_argument("query", nargs="?", help="Query to ask")
    parser.add_argument(
        "--inspect",
        metavar="RUN_ID",
        help="Inspect a past run (use 'last' for most recent)",
    )
    args = parser.parse_args()

    if args.inspect:
        inspect_run(args.inspect, DB_PATH)
        sys.exit(0)

    if not args.query:
        parser.print_help()
        sys.exit(1)

    print(f"\nQuery: {args.query}\n")
    run(args.query)


if __name__ == "__main__":
    main()
