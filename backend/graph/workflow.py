"""LangGraph StateGraph: supervisor plans pipelines; specialists run in sequence."""

from typing import TypedDict, Annotated
import operator
from langgraph.graph import StateGraph, END


def _merge_dicts(a: dict, b: dict) -> dict:
    merged = a.copy()
    merged.update(b)
    return merged


class AgentState(TypedDict):
    messages: Annotated[list, operator.add]
    task: str
    active_agent: str
    primary_agent: str
    agent_plan: list[str]
    plan_index: int
    results: Annotated[dict, _merge_dicts]
    memory_context: list[str]
    session_id: str


def route_from_supervisor(state: AgentState) -> str:
    """Route to the first agent in the plan."""
    return state["active_agent"]


def route_from_pipeline(state: AgentState) -> str:
    """Route to the next agent, or END when the pipeline is complete."""
    plan = state.get("agent_plan", [])
    idx = state.get("plan_index", 0)
    if idx < len(plan):
        return plan[idx]
    return END


def build_graph():
    from agents.supervisor import supervisor_node, pipeline_router_node
    from agents.researcher import researcher_node
    from agents.writer import writer_node
    from agents.scheduler import scheduler_node
    from agents.summariser import summariser_node

    graph = StateGraph(AgentState)

    graph.add_node("supervisor", supervisor_node)
    graph.add_node("pipeline_router", pipeline_router_node)
    graph.add_node("researcher", researcher_node)
    graph.add_node("writer", writer_node)
    graph.add_node("scheduler", scheduler_node)
    graph.add_node("summariser", summariser_node)

    graph.set_entry_point("supervisor")

    graph.add_conditional_edges(
        "supervisor",
        route_from_supervisor,
        {
            "researcher": "researcher",
            "writer": "writer",
            "scheduler": "scheduler",
            "summariser": "summariser",
        },
    )

    for agent in ["researcher", "writer", "scheduler", "summariser"]:
        graph.add_edge(agent, "pipeline_router")

    graph.add_conditional_edges(
        "pipeline_router",
        route_from_pipeline,
        {
            "researcher": "researcher",
            "writer": "writer",
            "scheduler": "scheduler",
            "summariser": "summariser",
            END: END,
        },
    )

    return graph.compile()


app_graph = build_graph()
