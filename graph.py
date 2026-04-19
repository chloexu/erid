from langgraph.graph import StateGraph, END
from state import AgentState
from agents.supervisor import supervisor_node
from agents.researcher import researcher_agent_node, researcher_tool_node, researcher_should_continue
from agents.summarizer import summarizer_node
from agents.decision import decision_agent_node, decision_tool_node, decision_should_continue


def build_graph(checkpointer=None):
    graph = StateGraph(AgentState)

    graph.add_node("supervisor", supervisor_node)
    graph.add_node("researcher", researcher_agent_node)
    graph.add_node("researcher_tools", researcher_tool_node)
    graph.add_node("summarizer", summarizer_node)
    graph.add_node("decision", decision_agent_node)
    graph.add_node("decision_tools", decision_tool_node)

    graph.set_entry_point("supervisor")

    # Supervisor routes: both research and codebase go to researcher
    graph.add_conditional_edges(
        "supervisor",
        lambda state: state["route"],
        {"research": "researcher", "codebase": "researcher", "decide": "decision"},
    )

    # Researcher loop -> summarizer
    graph.add_conditional_edges(
        "researcher",
        researcher_should_continue,
        {"researcher_tools": "researcher_tools", "summarize": "summarizer"},
    )
    graph.add_edge("researcher_tools", "researcher")
    graph.add_edge("summarizer", END)

    # Decision loop -> end (decision outputs answer directly via streaming)
    graph.add_conditional_edges(
        "decision",
        decision_should_continue,
        {"decision_tools": "decision_tools", "end": END},
    )
    graph.add_edge("decision_tools", "decision")

    return graph.compile(checkpointer=checkpointer)
