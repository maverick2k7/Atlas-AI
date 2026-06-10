"""MCP client with Google OAuth — Gmail and Calendar remote MCP servers.

Uses langchain-mcp-adapters MultiServerMCPClient with Bearer tokens from
credentials/token.json (auto-refreshed when expired).
"""

import json
import logging
from datetime import datetime
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from langchain_mcp_adapters.client import MultiServerMCPClient

logger = logging.getLogger(__name__)

CREDENTIALS_DIR = Path(__file__).resolve().parent.parent / "credentials"
TOKEN_PATH = CREDENTIALS_DIR / "token.json"

GMAIL_MCP_URL = "https://gmailmcp.googleapis.com/mcp/v1"
CALENDAR_MCP_URL = "https://calendarmcp.googleapis.com/mcp/v1"

# Subsets keep Groq free-tier requests under the 6000 TPM limit.
# All 12 Gmail tools ≈ 7900 tokens — too large for llama-3.1-8b-instant.
GMAIL_SUMMARY_TOOL_NAMES = frozenset({"search_threads", "get_thread"})
CALENDAR_SCHEDULER_TOOL_NAMES = frozenset({
    "list_events", "get_event", "list_calendars", "create_event", "update_event",
})


def _filter_tools(tools: list, allowed: frozenset[str]) -> list:
    filtered = [t for t in tools if t.name in allowed]
    if not filtered:
        logger.warning("[MCP] No tools matched filter %s", allowed)
    return filtered


def is_mcp_configured() -> bool:
    """True when OAuth token.json exists (user has run auth_setup.py)."""
    return TOKEN_PATH.exists()


def _save_token_data(data: dict) -> None:
    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(TOKEN_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _load_token_data() -> dict:
    if not TOKEN_PATH.exists():
        raise FileNotFoundError(
            f"OAuth token not found at {TOKEN_PATH}. "
            "Run: python backend/credentials/auth_setup.py"
        )
    with open(TOKEN_PATH, encoding="utf-8") as f:
        return json.load(f)


def get_oauth_credentials() -> Credentials:
    """Load Google OAuth credentials from disk, refreshing when expired."""
    data = _load_token_data()

    expiry_raw = data.get("expiry")
    expiry = datetime.fromisoformat(expiry_raw) if expiry_raw else None

    creds = Credentials(
        token=data.get("token"),
        refresh_token=data.get("refresh_token"),
        token_uri=data.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=data.get("client_id"),
        client_secret=data.get("client_secret"),
        scopes=data.get("scopes"),
        expiry=expiry,
    )

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        data.update({
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "scopes": list(creds.scopes) if creds.scopes else data.get("scopes"),
            "expiry": creds.expiry.isoformat() if creds.expiry else None,
        })
        _save_token_data(data)
        logger.info("[MCP] OAuth access token refreshed.")

    if not creds.token:
        raise ValueError("No valid access token. Re-run auth_setup.py.")

    return creds


def get_valid_access_token() -> str:
    """Load OAuth access token from disk, refreshing automatically if expired."""
    return get_oauth_credentials().token


def get_mcp_client() -> MultiServerMCPClient:
    """Create a MultiServerMCPClient with Bearer auth for both Google MCP servers."""
    token = get_valid_access_token()
    headers = {"Authorization": f"Bearer {token}"}

    return MultiServerMCPClient({
        "gmail": {
            "url": GMAIL_MCP_URL,
            "transport": "streamable_http",
            "headers": headers,
        },
        "google_calendar": {
            "url": CALENDAR_MCP_URL,
            "transport": "streamable_http",
            "headers": headers,
        },
    })


async def get_gmail_tools(*, for_summary: bool = True) -> list:
    """Return Gmail MCP tools. Default: minimal subset for summarisation."""
    client = get_mcp_client()
    tools = await client.get_tools(server_name="gmail")
    if for_summary:
        tools = _filter_tools(tools, GMAIL_SUMMARY_TOOL_NAMES)
    logger.info("[MCP] Gmail tools: %s", [t.name for t in tools])
    return tools


async def get_calendar_tools(*, for_scheduler: bool = True) -> list:
    """Return Calendar MCP tools. Default: subset for scheduling tasks."""
    client = get_mcp_client()
    tools = await client.get_tools(server_name="google_calendar")
    if for_scheduler:
        tools = _filter_tools(tools, CALENDAR_SCHEDULER_TOOL_NAMES)
    logger.info("[MCP] Calendar tools: %s", [t.name for t in tools])
    return tools


async def get_mcp_tools() -> list:
    """Return all tools from Gmail + Calendar MCP servers."""
    client = get_mcp_client()
    tools = await client.get_tools()
    logger.info("[MCP] All tools: %d available.", len(tools))
    return tools
