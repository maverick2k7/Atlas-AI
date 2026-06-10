"""Summariser agent: Gmail read, summarise, send, draft, reply, and inbox management.

Uses the Gmail REST API when OAuth is configured.
"""

import asyncio
from graph.workflow import AgentState
from memory.chroma_store import save_memory
from mcp_servers.client import get_gmail_tools, is_mcp_configured
from mcp_servers.gmail_api import execute_gmail_task
from config import settings
from agents.tool_runner import invoke_llm_with_tools, tool_outputs_indicate_mcp_failure
from langchain_core.messages import SystemMessage, HumanMessage
from llm import groq_llm

SYSTEM_PROMPT = """\
You are the Summariser agent in Atlas. You read and manage Gmail.

Use search_threads to find emails and get_thread to read them when using MCP tools."""


def _summarise_via_mcp(task: str, tools: list) -> str:
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


def summariser_node(state: AgentState) -> dict:
    """Summariser node: Gmail actions for the user."""
    task = state["task"]

    if not (settings.mcp_enabled and is_mcp_configured()):
        message = (
            "Gmail not connected. To enable email features:\n"
            "1. Place client_secret.json in backend/credentials/\n"
            "2. Add gmail.modify scope on Google Cloud OAuth consent screen\n"
            "3. Run: python backend/credentials/auth_setup.py\n"
            "4. Restart the backend"
        )
        save_memory(message, {"agent": "summariser", "task": task})
        print("  [Summariser] OAuth not configured — degraded mode.")
        return {
            "results": {"summary": message},
            "active_agent": "summariser",
        }

    result = ""
    try:
        print("  [Summariser] Running Gmail action via API...")
        result = execute_gmail_task(task)
    except Exception as exc:
        err = str(exc)
        print(f"  [Summariser] Gmail API error: {err}")
        if "insufficientPermissions" in err or "Insufficient Permission" in err:
            result = (
                "Gmail permission missing for this action. To fix:\n"
                "1. Google Cloud Console → OAuth consent screen → add gmail.modify scope\n"
                "2. Delete backend/credentials/token.json\n"
                "3. Run: python backend/credentials/auth_setup.py\n"
                "4. Restart the backend"
            )
        elif not result:
            result = f"Could not complete Gmail action: {exc}"

    if not result:
        print("  [Summariser] Trying Gmail MCP fallback...")
        try:
            try:
                tools = asyncio.run(get_gmail_tools())
            except RuntimeError:
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, get_gmail_tools())
                    tools = future.result()
            if tools:
                result = _summarise_via_mcp(task, tools)
        except Exception as exc:
            print(f"  [Summariser] MCP error: {exc}")

    if not result:
        result = (
            "Could not complete the Gmail action. Check that Gmail API is enabled and "
            "re-run: python backend/credentials/auth_setup.py"
        )

    save_memory(result, {"agent": "summariser", "task": task})
    print(f"  [Summariser] Done — saved {len(result)} chars to memory.")

    return {
        "results": {"summary": result},
        "active_agent": "summariser",
    }
