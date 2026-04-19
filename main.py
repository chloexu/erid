import sys
import argparse
from dotenv import load_dotenv

load_dotenv()  # must run before graph import — client is instantiated at module load time

from graph import build_graph, configure
from state import AgentState


def run(query: str, verbose: bool = False) -> None:
    configure(verbose=verbose)
    graph = build_graph()
    initial_state: AgentState = {
        "messages": [{"role": "user", "content": query}],
        "query": query,
        "iterations": 0,
    }

    for event in graph.stream(initial_state, stream_mode="updates"):
        if "tools" in event:
            messages = event["tools"]["messages"]
            tool_result_msg = messages[-1]
            assistant_msg = messages[-2] if len(messages) >= 2 else None

            id_to_name = {}
            if assistant_msg and assistant_msg.get("role") == "assistant":
                for block in assistant_msg.get("content", []):
                    if block.get("type") == "tool_use":
                        id_to_name[block["id"]] = block["name"]

            for block in tool_result_msg.get("content", []):
                if block.get("type") == "tool_result":
                    name = id_to_name.get(block.get("tool_use_id", ""), "tool")
                    if verbose:
                        print(f"\n[tool_result ← {name}] raw response:", flush=True)
                    else:
                        print(f"\n[tool_result] {name}", flush=True)
                    print(f"{block.get('content', '')}\n", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Erid research agent")
    parser.add_argument("query", nargs="+", help="Research question")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show granular loop and source labels")
    args = parser.parse_args()

    query = " ".join(args.query)
    print(f"\nQuery: {query}\n")
    run(query, verbose=args.verbose)
    print()
