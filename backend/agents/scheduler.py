"""Scheduler agent: manages Google Calendar events.

Uses the Google Calendar REST API when OAuth is configured (reliable with standard
Calendar API). MCP tools are skipped by default — their schemas exceed Groq free-tier
token limits.
"""

import asyncio
from langchain_core.messages import SystemMessage, HumanMessage
from graph.workflow import AgentState
from memory.chroma_store import save_memory
from mcp_servers.client import get_calendar_tools, is_mcp_configured
from mcp_servers.calendar_api import execute_calendar_task
from config import settings
from llm import groq_llm
from agents.tool_runner import invoke_llm_with_tools, tool_outputs_indicate_mcp_failure

SYSTEM_PROMPT = """\
You are the Scheduler agent in Atlas — Autonomous Task & Learning Agent System.

You have access to Google Calendar tools. Your job is to help the user manage \
their schedule by creating, querying, or updating calendar events.

Guidelines:
- Interpret the user's request and call the appropriate calendar tool(s).
- When creating an event, confirm the title, date, time, and duration.
- Always confirm what action was taken in your final response.
- If no suitable tool exists for the request, explain what you cannot do."""


def _schedule_via_mcp(task: str, tools: list) -> str:
    """Try Calendar MCP tools; returns empty string if MCP cannot complete the task."""
    llm = groq_llm(max_tokens=512)
    llm_with_tools = llm.bind_tools(tools)
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"Task: {task}"),
    ]
    try:
        response, all_messages = invoke_llm_with_tools(llm_with_tools, messages, tools)
    except Exception:
        return ""

    raw = response.content
    if isinstance(raw, list):
        raw = " ".join(
            part.get("text", "") if isinstance(part, dict) else str(part)
            for part in raw
        )
    result = str(raw).strip()
    if not result or tool_outputs_indicate_mcp_failure(all_messages):
        return ""
    return result


def scheduler_node(state: AgentState) -> dict:
    """Scheduler node: create or query calendar events for the user."""
    task = state["task"]

    if not (settings.mcp_enabled and is_mcp_configured()):
        message = (
            "Calendar not connected. To enable scheduling:\n"
            "1. Place client_secret.json in backend/credentials/\n"
            "2. Run: python backend/credentials/auth_setup.py\n"
            "3. Restart the backend"
        )
        save_memory(message, {"agent": "scheduler", "task": task})
        print("  [Scheduler] OAuth not configured — degraded mode.")
        return {
            "results": {"schedule": message},
            "active_agent": "scheduler",
        }

    result = ""
    try:
        print("  [Scheduler] Using Google Calendar API...")
        result = execute_calendar_task(task)
    except Exception as exc:
        print(f"  [Scheduler] Calendar API error: {exc}")

    if not result:
        print("  [Scheduler] Trying Calendar MCP tools...")
        try:
            try:
                tools = asyncio.run(get_calendar_tools())
            except RuntimeError:
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, get_calendar_tools())
                    tools = future.result()
            if tools:
                result = _schedule_via_mcp(task, tools)
        except Exception as exc:
            print(f"  [Scheduler] MCP error: {exc}")

    if not result:
        result = (
            "Could not complete the calendar action. Check that Google Calendar API "
            "is enabled in Google Cloud and re-run: python backend/credentials/auth_setup.py"
        )

    save_memory(result, {"agent": "scheduler", "task": task})
    print(f"  [Scheduler] Done — saved {len(result)} chars to memory.")

    return {
        "results": {"schedule": result},
        "active_agent": "scheduler",
    }
