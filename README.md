# Atlas — Multi-Agent AI Productivity System

> A supervisor agent reads your task in plain English and routes it to the right specialist — research, writing, calendar, or Gmail — with shared memory across sessions.

---

## What it does

Type a task in the chat UI. Atlas routes it to one specialist agent, runs the LangGraph pipeline, and streams the result back over WebSocket. Every agent response is saved to ChromaDB so future sessions can retrieve relevant context.

**Examples:**
- *"What are the latest developments in AI agents this week?"* → **Researcher**
- *"Draft a professional email asking for a deadline extension"* → **Writer**
- *"Schedule a study session for tomorrow at 3pm for 2 hours"* → **Scheduler**
- *"Summarise my last 5 unread emails"* → **Summariser**

---

## Architecture

```
User (React Chat UI)
        │
        │  WebSocket (FastAPI)
        ▼
┌─────────────────────────────┐
│      Supervisor Agent       │  ← LangGraph entry node
│  Pre-routes + LLM fallback  │  ← Groq llama-3.1-8b-instant
└────────────┬────────────────┘
             │ routes to one of:
    ┌────────┼──────────┬────────────┐
    ▼        ▼          ▼            ▼
Researcher  Writer  Scheduler  Summariser
 (Tavily)  (compose) (Calendar)  (Gmail)
    │        │          │            │
    └────────┴──────────┴────────────┘
                        │
                        ▼
          ┌─────────────────────────┐
          │   ChromaDB Memory Layer │
          │  sentence-transformers  │
          │  all-MiniLM-L6-v2      │
          └────────────┬────────────┘
                       │
          ┌────────────┴────────────┐
          ▼                         ▼
   Google Gmail API          Google Calendar API
   (primary path)            (primary path)
          │                         │
          └──────── MCP fallback ───┘
              (when configured)
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Agent framework | LangGraph (StateGraph, conditional edges) |
| LLM | Groq `llama-3.1-8b-instant` via `langchain-groq` |
| Gmail / Calendar | Google REST APIs (`google-api-python-client`) + OAuth 2.0 |
| MCP (optional) | `langchain-mcp-adapters` — fallback for Gmail/Calendar MCP servers |
| Vector DB | ChromaDB (local persistent store) |
| Embeddings | `sentence-transformers` — `all-MiniLM-L6-v2` |
| Web search | Tavily API |
| Backend | FastAPI + Uvicorn (WebSocket `/ws/chat`) |
| Frontend | React + Vite |
| Observability | LangSmith (optional) |

---

## Agents

| Agent | Routes when… | What it does |
|---|---|---|
| **Supervisor** | Every request | Pre-routes clear tasks; otherwise asks Groq to pick an agent |
| **Researcher** | Lookups, news, facts | Tavily web search + ChromaDB RAG |
| **Writer** | Draft/write/compose text | Produces email copy, reports, edits — **does not touch Gmail** |
| **Scheduler** | Calendar / scheduling | Creates and lists events via Google Calendar API |
| **Summariser** | Inbox / Gmail actions | Reads, summarises, sends, replies, drafts in Gmail, mark read, archive, delete, label |

**Routing note:** *"Draft a professional email…"* goes to **Writer** (text composition). *"Summarise my unread emails"* or *"Reply to my latest email"* goes to **Summariser** (real Gmail account actions).

---

## Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- [Groq API key](https://console.groq.com) (free tier)
- [Tavily API key](https://tavily.com) (free tier)
- *(Optional)* Google Cloud project for Gmail + Calendar

### 1. Backend

```bash
cd backend
python -m venv venv
.\venv\Scripts\activate          # Windows
# source venv/bin/activate       # macOS/Linux
pip install -r requirements.txt

copy ..\.env.example .env        # Windows — or cp on macOS/Linux
# Edit backend/.env — set GROQ_API_KEY and TAVILY_API_KEY

python -m uvicorn api.main:api --reload --port 8000
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173).

### 3. Gmail + Calendar (optional)

Enables the **Scheduler** and **Summariser** agents. Without this, those agents return setup instructions instead of failing the whole app.

1. **Google Cloud Console**
   - Create a project and enable **Gmail API** and **Google Calendar API**
   - Configure the OAuth consent screen and add scopes:
     - `gmail.readonly`, `gmail.send`, `gmail.compose`, `gmail.modify`, `calendar`
   - Create a **Desktop app** OAuth client and download the JSON

2. **Place credentials**
   ```
   backend/credentials/client_secret.json
   ```

3. **Authenticate once**
   ```bash
   python backend/credentials/auth_setup.py
   ```
   Opens a browser login and saves `backend/credentials/token.json`.

4. **Restart the backend**

See `atlas_mcp_oauth_setup.md` for a step-by-step Google Cloud walkthrough.

---

## Environment Variables

Create `backend/.env` (copy from `.env.example` at the project root):

```bash
GROQ_API_KEY=gsk_...              # Required — console.groq.com
TAVILY_API_KEY=tvly-...           # Required for Researcher
MCP_ENABLED=true                  # Set false to skip Gmail/Calendar entirely

# Optional — LangSmith tracing
LANGSMITH_API_KEY=lsv2_...
LANGSMITH_TRACING=false
LANGSMITH_PROJECT=atlas
```

---

## Project Structure

```
Atlas/
├── backend/
│   ├── agents/
│   │   ├── supervisor.py       # Orchestrator + routing
│   │   ├── routing.py          # Greetings, creator reply, pre-routing rules
│   │   ├── researcher.py       # Tavily + ChromaDB RAG
│   │   ├── writer.py           # Text drafting and editing
│   │   ├── scheduler.py        # Calendar via Google Calendar API
│   │   ├── summariser.py       # Gmail read + manage via Google Gmail API
│   │   └── tool_runner.py      # MCP tool loop (async ainvoke)
│   ├── mcp_servers/
│   │   ├── client.py           # OAuth token + MCP client
│   │   ├── gmail_api.py        # Gmail REST API actions
│   │   └── calendar_api.py     # Calendar REST API actions
│   ├── credentials/
│   │   └── auth_setup.py       # One-time Google OAuth login
│   ├── memory/
│   │   └── chroma_store.py     # save_memory / search_memory
│   ├── graph/
│   │   └── workflow.py         # LangGraph StateGraph
│   ├── api/
│   │   └── main.py             # FastAPI + WebSocket
│   ├── llm.py                  # Groq factory + rate-limit retry
│   └── config.py
├── frontend/src/
│   ├── ChatInterface.jsx
│   ├── AgentStatus.jsx
│   └── MessageBubble.jsx
├── evals/
│   ├── test_prompts.json
│   └── run_evals.py
└── README.md
```

---

## Evals

Routing accuracy is measured with deterministic rules (fast, no API keys):

```bash
cd backend
.\venv\Scripts\python.exe ..\evals\run_routing_eval.py
```

This runs **30 single-agent** routing prompts plus **3 multi-agent pipeline** prompts.
Results: `evals/results.csv` and `evals/multi_results.csv`.

Full end-to-end eval (runs real agents — slower, needs API keys):

```bash
.\venv\Scripts\python.exe ..\evals\run_evals.py
```

---

## Key Concepts

| Term | Meaning |
|---|---|
| **LangGraph** | Graph of agent nodes and routing edges — deterministic multi-agent control |
| **AgentState** | Shared typed state every node reads and writes |
| **RAG** | Retrieve past session context from ChromaDB before responding |
| **Pre-routing** | Rule-based routing in `routing.py` before the LLM supervisor decides |
| **Google REST APIs** | Primary integration for Gmail/Calendar (reliable, low token overhead) |
| **MCP** | Optional fallback protocol for Google's remote Gmail/Calendar MCP servers |

---

## Common Errors

| Error | Fix |
|---|---|
| `ModuleNotFoundError` | Activate venv: `.\venv\Scripts\activate` |
| Groq `413` / `rate_limit_exceeded` | Request too large for free tier — retry; Gmail/Calendar use REST APIs to avoid oversized MCP tool schemas |
| `Connection refused` on WebSocket | Start backend: `python -m uvicorn api.main:api --reload --port 8000` |
| Gmail `Insufficient Permission` | Add `gmail.modify` on OAuth consent screen, delete `token.json`, re-run `auth_setup.py` |
| Calendar/Gmail not connected | Run OAuth setup; agents degrade gracefully with instructions |
| Stale backend after code changes | Kill all processes on port 8000 and restart uvicorn |

---

*Built by Hamza Zeeshan — FAST NUCES Islamabad, Class of 2029*

*Stack: LangGraph · Groq · ChromaDB · Google APIs · FastAPI · React*
