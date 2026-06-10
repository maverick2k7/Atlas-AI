"""FastAPI application: WebSocket /ws/chat + REST /health.

Streams LangGraph agent output to the React frontend over WebSocket.
Each message chunk is sent as JSON as soon as a node completes.

Run from the backend/ directory:
    .\\venv\\Scripts\\python.exe -m uvicorn api.main:api --reload --port 8000
"""

import os
import json
import uuid
import logging

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from agents.routing import get_direct_reply

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# LangSmith tracing — must be set before importing graph (which imports LLMs)
# ---------------------------------------------------------------------------

# LangSmith tracing — disabled if key is missing/invalid (avoids 403 retry loops)
_ls_key = settings.langsmith_api_key
if _ls_key and settings.langsmith_tracing.lower() == "true":
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"]     = _ls_key
    os.environ["LANGCHAIN_PROJECT"]     = settings.langsmith_project
else:
    os.environ["LANGCHAIN_TRACING_V2"] = "false"

# Deferred import so tracing env vars are set first
from graph.workflow import app_graph  # noqa: E402

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

api = FastAPI(
    title="Atlas API",
    description="Atlas — Autonomous Task & Learning Agent System. WebSocket streaming backend.",
    version="1.0.0",
)

api.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# REST endpoints
# ---------------------------------------------------------------------------

@api.get("/health")
async def health():
    """Health check — confirms the API is running and lists available agents."""
    from mcp_servers.client import is_mcp_configured

    return {
        "status": "ok",
        "version": "mcp-oauth-v1",
        "mcp_configured": is_mcp_configured(),
        "agents": ["researcher", "writer", "scheduler", "summariser"],
    }


# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------

# Maps specialist node names to their results dict key
_RESULT_KEYS = {
    "researcher": "research",
    "writer": "writing",
    "scheduler": "schedule",
    "summariser": "summary",
}


def _friendly_error(exc: Exception) -> str:
    """Turn raw API errors into short user-facing messages."""
    msg = str(exc)
    if "429" in msg or "rate_limit" in msg.lower():
        return "Groq rate limit reached — wait about 15 seconds and try again."
    if "413" in msg or "too large" in msg.lower():
        return "Request too large for Groq free tier — try a shorter prompt or wait a moment."
    return msg


@api.websocket("/ws/chat")
async def chat_ws(ws: WebSocket):
    """Stream agent responses over WebSocket.

    Protocol:
      Client sends:  {"message": str, "session_id": str}
      Server sends:  {"agent": str, "token": str, "done": false}  (agent output)
      Server sends:  {"done": true}  (after stream completes)
      Server sends:  {"error": str, "done": true}  (on any exception)
    """
    await ws.accept()
    logger.info("[WS] Client connected.")

    while True:
        # ---- Receive user message ----
        try:
            data = await ws.receive_json()
        except WebSocketDisconnect:
            logger.info("[WS] Client disconnected.")
            break
        except Exception as exc:
            logger.warning(f"[WS] Receive error: {exc}")
            break

        message    = data.get("message", "")
        session_id = data.get("session_id", str(uuid.uuid4()))

        if not message:
            await ws.send_json({"error": "Empty message received.", "done": True})
            continue

        logger.info(f"[WS] Task received: {message!r}  session={session_id}")

        # ---- Greetings / meta questions — respond directly, skip the agent graph ----
        direct_reply = get_direct_reply(message)
        if direct_reply:
            await ws.send_json({
                "agent": "supervisor",
                "token": direct_reply,
                "done": False,
            })
            await ws.send_json({"done": True})
            continue

        # ---- Build initial AgentState ----
        initial_state = {
            "task":           message,
            "messages":       [{"role": "user", "content": message}],
            "results":        {},
            "active_agent":   "",
            "primary_agent":  "",
            "agent_plan":     [],
            "plan_index":     0,
            "memory_context": [],
            "session_id":     session_id,
        }

        # ---- Stream graph execution — send each agent's result when its node completes ----
        try:
            async for event in app_graph.astream(initial_state, stream_mode="updates"):
                for node_name, update in event.items():
                    if node_name in ("supervisor", "pipeline_router"):
                        routed = update.get("active_agent", "")
                        if routed:
                            await ws.send_json({
                                "agent": routed,
                                "token": "",
                                "done": False,
                            })
                        continue

                    result_key = _RESULT_KEYS.get(node_name)
                    if not result_key:
                        continue

                    content = update.get("results", {}).get(result_key, "")
                    if content:
                        await ws.send_json({
                            "agent": node_name,
                            "token": content,
                            "done": False,
                        })

            await ws.send_json({"done": True})
            logger.info("[WS] Stream complete.")

        except WebSocketDisconnect:
            logger.info("[WS] Client disconnected mid-stream.")
            break
        except Exception as exc:
            logger.error(f"[WS] Graph error: {exc}", exc_info=True)
            try:
                await ws.send_json({"error": _friendly_error(exc), "done": True})
            except Exception:
                pass  # Connection already closed
