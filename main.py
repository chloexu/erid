import sys
from dotenv import load_dotenv
from graph import build_graph
from state import AgentState

load_dotenv()


def run(query: str) -> str:
    graph = build_graph()
    initial_state: AgentState = {
        "messages": [{"role": "user", "content": query}],
        "query": query,
        "iterations": 0,
    }
    final_state = graph.invoke(initial_state)
    last_message = final_state["messages"][-1]
    content = last_message.get("content", [])
    for block in content:
        if isinstance(block, dict) and block.get("type") == "text":
            return block["text"]
    return "No answer produced."


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) or "What is LangGraph and how does it work?"
    print(f"\nQuery: {query}\n")
    answer = run(query)
    print(f"Answer:\n{answer}\n")
