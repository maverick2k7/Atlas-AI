"""Supervisor agent: plans multi-agent pipelines and routes to specialists."""

from langchain_core.messages import SystemMessage, HumanMessage
from graph.workflow import AgentState
from memory.chroma_store import search_memory
from agents.routing import get_direct_reply, plan_agents
from llm import groq_llm, invoke_llm

VALID_AGENTS = {"researcher", "writer", "scheduler", "summariser"}

SYSTEM_PROMPT = """\
You are the Supervisor agent in Atlas — Autonomous Task & Learning Agent System.

Pick the ONE best specialist for this task:

1. researcher — Web search, news, facts, research questions
2. writer — Draft/edit text (emails, reports) WITHOUT accessing Gmail inbox
3. scheduler — Calendar events, meetings, availability
4. summariser — User's Gmail inbox (read, summarise, send, reply, manage)

Respond with ONLY one word: researcher, writer, scheduler, or summariser."""


def _llm_pick_agent(task: str, memory_results: list[str]) -> str:
    context_block = ""
    if memory_results:
        context_block = (
            "\n\nRelevant past context:\n"
            + "\n".join(f"- {m}" for m in memory_results)
        )
    response = invoke_llm(
        groq_llm(max_tokens=32),
        [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=f"User task: {task}{context_block}"),
        ],
    )
    raw = response.content
    if isinstance(raw, list):
        raw = " ".join(
            part.get("text", "") if isinstance(part, dict) else str(part)
            for part in raw
        )
    chosen = str(raw).strip().lower()
    if chosen not in VALID_AGENTS:
        for agent_name in VALID_AGENTS:
            if agent_name in chosen:
                return agent_name
        return "researcher"
    return chosen


def supervisor_node(state: AgentState) -> dict:
    """Plan which agent(s) to run and set the first step."""
    task = state["task"]

    memory_results: list[str] = []
    if get_direct_reply(task) is None and len(task.strip()) >= 15:
        memory_results = [m[:500] for m in search_memory(task, n=3)]

    agent_plan = plan_agents(task)
    if not agent_plan:
        agent_plan = [_llm_pick_agent(task, memory_results)]
        print(f"  [Supervisor] LLM plan -> {' -> '.join(agent_plan)}")
    else:
        print(f"  [Supervisor] Plan -> {' -> '.join(agent_plan)}")

    return {
        "agent_plan": agent_plan,
        "plan_index": 0,
        "primary_agent": agent_plan[0],
        "active_agent": agent_plan[0],
        "memory_context": memory_results,
    }


def pipeline_router_node(state: AgentState) -> dict:
    """Advance to the next agent in the pipeline after a specialist completes."""
    plan = state.get("agent_plan", [])
    idx = state.get("plan_index", 0) + 1
    update: dict = {"plan_index": idx}

    if idx < len(plan):
        update["active_agent"] = plan[idx]
        print(f"  [Pipeline] Next -> {plan[idx]} ({idx + 1}/{len(plan)})")
    else:
        print(f"  [Pipeline] Complete ({len(plan)} agent(s))")

    return update
