# Atlas — MCP + OAuth Setup Guide
> Feed this file to Antigravity before starting. Follow every step in order. Do not skip ahead.

---

## Context

Atlas uses two Google MCP servers:
- **Gmail MCP** — `https://gmailmcp.googleapis.com/mcp/v1`
- **Google Calendar MCP** — `https://calendarmcp.googleapis.com/mcp/v1`

Both require OAuth 2.0 authentication. This guide covers:
1. Google Cloud Console setup (one-time, done in browser)
2. Local authentication (generates the token your code uses)
3. Project code setup (`mcp/client.py`)
4. Verification test

---

## Phase 1 — Google Cloud Console Setup

### Step 1 — Create a Google Cloud Project

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Click the project dropdown at the top of the page
3. Click **New Project**
4. Name it `atlas`
5. Click **Create**
6. Wait for the project to be created, then make sure it's selected in the dropdown

---

### Step 2 — Enable Gmail and Calendar APIs

1. In the top search bar, search for `Gmail API`
2. Click on it → click **Enable**
3. Go back to the search bar, search for `Google Calendar API`
4. Click on it → click **Enable**

---

### Step 3 — Configure the OAuth Consent Screen

1. In the left sidebar go to **APIs & Services → OAuth consent screen**
2. Choose **External** → click **Create**
3. Fill in:
   - App name: `Atlas`
   - User support email: your Gmail address
   - Developer contact email: your Gmail address
4. Click **Save and Continue**
5. On the **Scopes** page, click **Add or Remove Scopes** and add these three:
   ```
   https://www.googleapis.com/auth/gmail.readonly
   https://www.googleapis.com/auth/gmail.send
   https://www.googleapis.com/auth/calendar
   ```
6. Click **Update** → **Save and Continue**
7. On the **Test Users** page, click **Add Users** and add your own Gmail address
8. Click **Save and Continue** → **Back to Dashboard**

---

### Step 4 — Create OAuth Credentials

1. Go to **APIs & Services → Credentials**
2. Click **Create Credentials → OAuth Client ID**
3. Application type: **Desktop app**
4. Name: `atlas-local`
5. Click **Create**
6. A popup appears with your Client ID and Client Secret — click **Download JSON**
7. The file downloads as something like `client_secret_1234abc.json`

---

### Step 5 — Place the Credentials File

1. In the project, create this folder if it doesn't exist:
   ```
   backend/credentials/
   ```
2. Move the downloaded JSON file into that folder and rename it to exactly:
   ```
   backend/credentials/client_secret.json
   ```
3. Open `.gitignore` and add these two lines:
   ```
   backend/credentials/client_secret.json
   backend/credentials/token.json
   ```

---

## Phase 2 — Local Authentication

### Step 6 — Install Auth Libraries

Run these in the terminal with the backend venv activated:

```bash
cd backend
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install google-auth-oauthlib google-auth-httplib2
```

---

### Step 7 — Create the One-Time Auth Script

Create this file at `backend/credentials/auth_setup.py`:

```python
# backend/credentials/auth_setup.py
# PURPOSE: Run this ONCE to log in via browser and save a reusable token.
# After token.json is created, you never need to run this again
# (unless the token is deleted or expires permanently).

from google_auth_oauthlib.flow import InstalledAppFlow
import json

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar",
]

# Load client_secret.json and start the OAuth flow
# run_local_server(port=0) opens your browser and picks a free port
flow = InstalledAppFlow.from_client_secrets_file(
    "backend/credentials/client_secret.json",
    scopes=SCOPES
)
creds = flow.run_local_server(port=0)

# Save all credential fields to token.json so the app can reuse them
token_data = {
    "token":         creds.token,           # short-lived access token (~1hr)
    "refresh_token": creds.refresh_token,   # long-lived, used to get new tokens
    "token_uri":     creds.token_uri,
    "client_id":     creds.client_id,
    "client_secret": creds.client_secret,
    "scopes":        creds.scopes,
}

with open("backend/credentials/token.json", "w") as f:
    json.dump(token_data, f, indent=2)

print("Token saved to backend/credentials/token.json")
```

---

### Step 8 — Run the Auth Script

Run this from the **project root** (not from inside backend/):

```bash
cd atlas    # make sure you're at project root
python backend/credentials/auth_setup.py
```

What happens:
1. A browser window opens automatically
2. Log in with your Google account
3. You'll see a warning — "Google hasn't verified this app" — click **Continue**
4. Grant the permissions (Gmail read, Gmail send, Calendar)
5. Browser shows "The authentication flow has completed"
6. Terminal prints: `Token saved to backend/credentials/token.json`

The file `backend/credentials/token.json` now exists. This is what your code uses to authenticate at runtime.

---

## Phase 3 — Project Code Setup

### Step 9 — Write `backend/mcp/client.py`

Replace the contents of `backend/mcp/client.py` with this:

```python
# backend/mcp/client.py
# PURPOSE: Creates the shared MCP client used by scheduler.py and summariser.py.
# Both agents import get_mcp_client() from here — single source of truth for MCP config.

import json
from pathlib import Path
from langchain_mcp_adapters.client import MultiServerMCPClient


def load_token() -> str:
    """
    Reads the OAuth access token from token.json.

    WHY: Google's MCP servers are HTTP endpoints that require a Bearer token
    in the Authorization header. Without it, the server rejects the connection.
    The token was generated in Phase 2 by auth_setup.py.
    """
    token_path = Path(__file__).parent.parent / "credentials" / "token.json"
    with open(token_path) as f:
        data = json.load(f)
    return data["token"]


def get_mcp_client() -> MultiServerMCPClient:
    """
    Creates and returns a MultiServerMCPClient connected to Gmail and Google Calendar.

    WHY MultiServerMCPClient:
    - Manages connections to multiple MCP servers in one object
    - Each agent calls .get_tools(server_name=...) to get only the tools it needs
    - langchain-mcp-adapters wraps MCP tools as LangChain tools so Claude can use them

    WHY streamable_http:
    - Google's MCP servers are remote (hosted by Google), not local processes
    - streamable_http is the correct transport for remote MCP servers
    - stdio transport is only for local MCP processes running on your machine

    WHY the same token for both servers:
    - Both Gmail and Calendar are Google services
    - The same OAuth credential (with the right scopes) covers both
    """
    token = load_token()
    auth_header = {"Authorization": f"Bearer {token}"}

    return MultiServerMCPClient(
        {
            "gmail": {
                "url": "https://gmailmcp.googleapis.com/mcp/v1",
                "transport": "streamable_http",
                "headers": auth_header,
            },
            "google_calendar": {
                "url": "https://calendarmcp.googleapis.com/mcp/v1",
                "transport": "streamable_http",
                "headers": auth_header,
            },
        }
    )
```

---

### Step 10 — Add MCP Tool Binding to `scheduler.py`

In `backend/agents/scheduler.py`, add these imports at the top:

```python
from mcp.client import get_mcp_client
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage
```

Add this helper function (outside `scheduler_node`):

```python
async def get_calendar_tools():
    """
    Opens an MCP connection to Google Calendar and returns its tools
    as LangChain-compatible tool objects.

    WHY async: MCP connections are network calls. async prevents blocking
    the entire FastAPI server while waiting for the connection to open.

    WHY server_name="google_calendar": Fetches only calendar tools,
    not Gmail tools. Keeps each agent focused on its own responsibility.
    """
    async with get_mcp_client() as client:
        tools = await client.get_tools(server_name="google_calendar")
        return tools
```

Inside `scheduler_node`, add this block where the calendar action should happen:

```python
# Get calendar tools from MCP
calendar_tools = await get_calendar_tools()

# Create the LLM and bind the tools to it
# bind_tools() tells Claude: "these tools exist, you may call them"
# Claude reads the task and decides WHICH tool to call and with WHAT arguments
llm = ChatAnthropic(model="claude-sonnet-4-20250514")
llm_with_tools = llm.bind_tools(calendar_tools)

response = await llm_with_tools.ainvoke([
    HumanMessage(content=f"""
        You are a scheduling assistant with access to Google Calendar.

        Task: {state['task']}

        Use the available calendar tools to complete this task.
        Confirm what action you took.
    """)
])

# Save result to shared state
state["results"]["schedule"] = response.content
state["active_agent"] = "scheduler"
```

---

### Step 11 — Add MCP Tool Binding to `summariser.py`

In `backend/agents/summariser.py`, add these imports at the top:

```python
from mcp.client import get_mcp_client
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage
```

Add this helper function (outside `summariser_node`):

```python
async def get_gmail_tools():
    """
    Opens an MCP connection to Gmail and returns its tools
    as LangChain-compatible tool objects.

    Same pattern as get_calendar_tools() but scoped to Gmail only.
    """
    async with get_mcp_client() as client:
        tools = await client.get_tools(server_name="gmail")
        return tools
```

Inside `summariser_node`, add this block where the email action should happen:

```python
# Get Gmail tools from MCP
gmail_tools = await get_gmail_tools()

# Bind tools to Claude — same pattern as scheduler
llm = ChatAnthropic(model="claude-sonnet-4-20250514")
llm_with_tools = llm.bind_tools(gmail_tools)

response = await llm_with_tools.ainvoke([
    HumanMessage(content=f"""
        You are an email assistant with access to Gmail.

        Task: {state['task']}

        Use the available Gmail tools to read emails and complete this task.
        Provide a clear summary of what you found.
    """)
])

# Save result to shared state
state["results"]["summary"] = response.content
state["active_agent"] = "summariser"
```

---

## Phase 4 — Verification

### Step 12 — Run the MCP Test

Create `backend/test_mcp.py`:

```python
# backend/test_mcp.py
# PURPOSE: Verify MCP connections are working before running the full system.
# Run this after completing all setup steps. If tool names print, everything works.

import asyncio
from mcp.client import get_mcp_client

async def test():
    print("Connecting to MCP servers...")

    async with get_mcp_client() as client:

        gmail_tools = await client.get_tools(server_name="gmail")
        print(f"\nGmail tools ({len(gmail_tools)} found):")
        for t in gmail_tools:
            print(f"   - {t.name}")

        calendar_tools = await client.get_tools(server_name="google_calendar")
        print(f"\nGoogle Calendar tools ({len(calendar_tools)} found):")
        for t in calendar_tools:
            print(f"   - {t.name}")

    print("\nMCP setup complete. Both servers are connected.")

asyncio.run(test())
```

Run it:

```bash
cd backend
python test_mcp.py
```

**Expected output:**
```
Connecting to MCP servers...

Gmail tools (3 found):
   - list_messages
   - get_message
   - send_message

Google Calendar tools (3 found):
   - list_events
   - create_event
   - update_event

MCP setup complete. Both servers are connected.
```

---

## Troubleshooting

| Problem | Cause | Fix |
|---|---|---|
| `FileNotFoundError: client_secret.json` | File not placed correctly | Check path is exactly `backend/credentials/client_secret.json` |
| `FileNotFoundError: token.json` | auth_setup.py not run yet | Run `python backend/credentials/auth_setup.py` from project root |
| Browser doesn't open during auth | Running in headless environment | Run auth_setup.py on your local machine, then copy token.json to server |
| `empty list` from `get_tools()` | Token not attached or expired | Check `Authorization` header in `client.py`; re-run auth_setup.py if expired |
| `401 Unauthorized` from MCP server | Token expired (tokens last ~1hr) | Re-run `python backend/credentials/auth_setup.py` to get a fresh token |
| `invalid_scope` error during auth | Scope not added in consent screen | Go back to Cloud Console → OAuth consent screen → add the missing scope |
| `Access blocked: Atlas has not completed verification` | App in testing mode | Add your Gmail as a test user in the consent screen (Step 3, point 7) |

---

## File Checklist

After completing all steps, verify these files exist:

```
backend/
├── credentials/
│   ├── client_secret.json    ✅ downloaded from Google Cloud Console
│   ├── token.json            ✅ generated by auth_setup.py
│   └── auth_setup.py         ✅ one-time script (keep for token refresh)
├── mcp/
│   ├── __init__.py
│   └── client.py             ✅ updated with token auth
├── agents/
│   ├── scheduler.py          ✅ MCP tool binding added
│   └── summariser.py         ✅ MCP tool binding added
└── test_mcp.py               ✅ run to verify everything works
```

---

## Token Refresh Note

The `token` field in `token.json` expires after approximately **1 hour**. The `refresh_token` field never expires (unless you revoke access in your Google account).

If you get `401 Unauthorized` errors after the first hour, re-run the auth script to get a fresh token:

```bash
python backend/credentials/auth_setup.py
```

For production deployment on Railway, auto-refresh logic will need to be added to `client.py`. Flag this as a follow-up task after local development is complete.

---

*Atlas — Built by Hamza Zeeshan, FAST NUCES '29*
