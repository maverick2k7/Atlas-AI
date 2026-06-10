<<<<<<< HEAD
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
=======
<div align="center">

# 🌐 ATLAS AI

### Multi-Agent AI Productivity System

*Type a task. Atlas thinks, routes, and executes — across the web, your calendar, and your inbox.*

<br/>

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-Agents-1C3F6E?style=for-the-badge&logo=chainlink&logoColor=white)](https://langchain-ai.github.io/langgraph/)
[![Groq](https://img.shields.io/badge/Groq-llama--3.1--8b-F55036?style=for-the-badge&logo=meta&logoColor=white)](https://groq.com)
[![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-Frontend-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_Memory-E07B39?style=for-the-badge)](https://www.trychroma.com)
[![MCP](https://img.shields.io/badge/MCP-Gmail_%26_Calendar-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://modelcontextprotocol.io)

<br/>

> **"Research the latest news on LangGraph, write me a summary email, and schedule 30 minutes to read it tomorrow."**
>
> *— Atlas handles all of it. One prompt. Four agents. Zero tab-switching.*

<br/>

<!-- Add your demo GIF here -->
<!-- ![Atlas Demo](assets/demo.gif) -->

---

</div>

## What is Atlas?

Atlas is a **multi-agent AI productivity system** where a supervisor agent reads your plain-English task, breaks it down, and routes it to the right specialist — instantly. No menus. No mode-switching. Just one chat interface backed by four agents that share memory across every session.

Most AI tools are wrappers. Atlas is an **orchestrated pipeline** — the kind production AI teams actually build.

---

## Agents

| Agent | Trigger phrases | What it does |
|---|---|---|
| 🧭 **Supervisor** | *(every request)* | Reads the task, searches past context, routes to the right agent(s) |
| 🔍 **Researcher** | *"latest news on…", "look up…", "what is…"* | Tavily web search + ChromaDB RAG — synthesised, not just linked |
| ✍️ **Writer** | *"draft…", "write…", "compose…"* | Emails, reports, summaries — polished output, no Gmail touch |
| 📅 **Scheduler** | *"schedule…", "add to calendar…", "remind me…"* | Creates and queries real Google Calendar events via MCP |
| 📬 **Summariser** | *"summarise my emails…", "reply to…", "archive…"* | Full Gmail management — read, send, reply, label, delete via MCP |
>>>>>>> 4eeae70feaaad01e65d063213eb98ab7a3ededb2

---

## Architecture

```
User (React Chat UI)
        │
<<<<<<< HEAD
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

=======
        │  WebSocket
        ▼
┌───────────────────────────┐
│      Supervisor Agent     │  ← LangGraph entry node
│  Pre-routes + LLM routing │  ← Groq llama-3.1-8b-instant
└──────────┬────────────────┘
           │  routes to one or more of:
   ┌───────┼────────┬────────────┐
   ▼       ▼        ▼            ▼
Researcher Writer Scheduler Summariser
(Tavily)  (draft) (Calendar) (Gmail)
   │       │        │            │
   └───────┴────────┴────────────┘
                    │
                    ▼
      ┌─────────────────────────┐
      │   ChromaDB Memory Layer │  ← Persistent vector store
      │  sentence-transformers  │  ← Semantic search across all sessions
      │  all-MiniLM-L6-v2      │
      └────────────┬────────────┘
                   │
      ┌────────────┴────────────┐
      ▼                         ▼
Gmail MCP Server       Google Calendar MCP
(read/draft/send/      (create/update/query
 label/archive)         events)
```

**Single message data flow:**

1. User sends message over WebSocket from React UI
2. `AgentState` is created — task, session ID, empty results
3. LangGraph enters at `supervisor_node`
4. Supervisor queries ChromaDB for relevant past context
5. Supervisor calls Groq to decide which agent(s) to invoke
6. Specialist agent(s) run — each queries memory, uses tools, saves output to ChromaDB
7. Results stream back over WebSocket in real time
8. React renders the response with a live agent status badge

>>>>>>> 4eeae70feaaad01e65d063213eb98ab7a3ededb2
---

## Tech Stack

| Layer | Technology |
|---|---|
<<<<<<< HEAD
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
=======
| Agent framework | LangGraph — `StateGraph`, conditional edges, async streaming |
| LLM | Groq `llama-3.1-8b-instant` via `langchain-groq` |
| MCP client | `langchain-mcp-adapters` — `MultiServerMCPClient` |
| Vector DB | ChromaDB — local persistent store |
| Embeddings | `sentence-transformers` — `all-MiniLM-L6-v2` (384-dim, free) |
| Web search | Tavily API |
| Backend | FastAPI + Uvicorn — WebSocket `/ws/chat` |
| Frontend | React + Vite |
| Observability | LangSmith — visual agent trace debugger |
| Deployment | Railway (backend) + Vercel (frontend) |

---

## Eval Results

Routing accuracy measured with 30 deterministic single-agent prompts (no API keys needed):

| Metric | Score |
|---|---|
| Supervisor routing accuracy | **83% (30 prompts)** |
| Multi-agent pipeline completion | **3 / 3 pipelines** |
| Avg supervisor latency | ~1.2s |

Run evals yourself:

```bash
# Fast routing eval — no API keys needed
cd backend
.\venv\Scripts\python.exe ..\evals\run_routing_eval.py

# Full end-to-end eval — needs API keys
.\venv\Scripts\python.exe ..\evals\run_evals.py
```

Results saved to `evals/results.csv` and `evals/multi_results.csv`.
>>>>>>> 4eeae70feaaad01e65d063213eb98ab7a3ededb2

---

## Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
<<<<<<< HEAD
- [Groq API key](https://console.groq.com) (free tier)
- [Tavily API key](https://tavily.com) (free tier)
- *(Optional)* Google Cloud project for Gmail + Calendar

### 1. Backend
=======
- [Groq API key](https://console.groq.com) — free tier
- [Tavily API key](https://tavily.com) — free tier (1,000 searches/month)
- *(Optional)* Google Cloud project for Gmail + Calendar

### 1. Clone & configure

```bash
git clone https://github.com/YOUR_USERNAME/atlas-ai.git
cd atlas-ai
cp .env.example backend/.env
# Edit backend/.env — add your API keys
```

### 2. Backend
>>>>>>> 4eeae70feaaad01e65d063213eb98ab7a3ededb2

```bash
cd backend
python -m venv venv
<<<<<<< HEAD
.\venv\Scripts\activate          # Windows
# source venv/bin/activate       # macOS/Linux
pip install -r requirements.txt

copy ..\.env.example .env        # Windows — or cp on macOS/Linux
# Edit backend/.env — set GROQ_API_KEY and TAVILY_API_KEY

python -m uvicorn api.main:api --reload --port 8000
```

### 2. Frontend
=======

# Windows
.\venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
python -m uvicorn api.main:api --reload --port 8000
```

### 3. Frontend
>>>>>>> 4eeae70feaaad01e65d063213eb98ab7a3ededb2

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173).

<<<<<<< HEAD
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
=======
### 4. Gmail + Calendar *(optional)*

Without this, Scheduler and Summariser return helpful setup instructions instead of failing.

```bash
# 1. Create a Google Cloud project
#    Enable Gmail API and Google Calendar API
#    Configure OAuth consent screen with these scopes:
#    gmail.readonly, gmail.send, gmail.compose, gmail.modify, calendar
#    Create a Desktop app OAuth client, download the JSON

# 2. Place credentials
cp your-downloaded-file.json backend/credentials/client_secret.json

# 3. One-time browser authentication
python backend/credentials/auth_setup.py

# 4. Restart the backend
```

Full walkthrough: `atlas_mcp_oauth_setup.md`
>>>>>>> 4eeae70feaaad01e65d063213eb98ab7a3ededb2

---

## Environment Variables

<<<<<<< HEAD
Create `backend/.env` (copy from `.env.example` at the project root):

```bash
GROQ_API_KEY=gsk_...              # Required — console.groq.com
TAVILY_API_KEY=tvly-...           # Required for Researcher
MCP_ENABLED=true                  # Set false to skip Gmail/Calendar entirely
=======
```bash
# backend/.env  —  never commit this file

GROQ_API_KEY=gsk_...               # Required — console.groq.com (free)
TAVILY_API_KEY=tvly-...            # Required for Researcher — tavily.com (free)
MCP_ENABLED=true                   # Set false to skip Gmail/Calendar entirely
>>>>>>> 4eeae70feaaad01e65d063213eb98ab7a3ededb2

# Optional — LangSmith tracing
LANGSMITH_API_KEY=lsv2_...
LANGSMITH_TRACING=false
LANGSMITH_PROJECT=atlas
```

---

## Project Structure

```
<<<<<<< HEAD
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
=======
atlas/
├── backend/
│   ├── agents/
│   │   ├── supervisor.py       # Orchestrator: reads task, decides routing
│   │   ├── routing.py          # Greetings, pre-routing rules
│   │   ├── researcher.py       # Tavily search + ChromaDB RAG
│   │   ├── writer.py           # LLM drafting and editing
│   │   ├── scheduler.py        # Google Calendar via MCP
│   │   └── summariser.py       # Gmail read/manage via MCP
│   ├── mcp_servers/
│   │   ├── client.py           # MultiServerMCPClient config
│   │   ├── gmail_api.py        # Gmail REST API fallback
│   │   └── calendar_api.py     # Calendar REST API fallback
>>>>>>> 4eeae70feaaad01e65d063213eb98ab7a3ededb2
│   ├── credentials/
│   │   └── auth_setup.py       # One-time Google OAuth login
│   ├── memory/
│   │   └── chroma_store.py     # save_memory / search_memory
│   ├── graph/
<<<<<<< HEAD
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
=======
│   │   └── workflow.py         # LangGraph StateGraph: all nodes + edges
│   ├── api/
│   │   └── main.py             # FastAPI app, WebSocket /ws/chat
│   ├── llm.py                  # Groq factory + rate-limit retry
│   └── config.py               # Centralised settings via pydantic-settings
├── frontend/src/
│   ├── ChatInterface.jsx        # Main chat + WebSocket logic
│   ├── AgentStatus.jsx          # Live badge: "Researcher thinking..."
│   └── MessageBubble.jsx        # Per-message component with agent label
├── evals/
│   ├── test_prompts.json        # 30 test tasks across all 4 agents
│   └── run_evals.py             # Routing accuracy benchmark
├── .env.example
>>>>>>> 4eeae70feaaad01e65d063213eb98ab7a3ededb2
└── README.md
```

---

<<<<<<< HEAD
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
=======
## Key Concepts

| Term | What it means in Atlas |
|---|---|
| **LangGraph** | Graph of agent nodes and routing edges — deterministic multi-agent control flow |
| **AgentState** | Shared typed dict every node reads from and writes to — single source of truth for the pipeline |
| **RAG** | Before generating, each agent retrieves relevant past context from ChromaDB to ground its answer |
| **Pre-routing** | Rule-based routing in `routing.py` before the LLM supervisor decides — faster and cheaper |
| **MCP** | Model Context Protocol — connects agents to Gmail and Google Calendar without custom API wrappers |
| **Conditional edges** | LangGraph routing — supervisor output determines which specialist node runs next |
>>>>>>> 4eeae70feaaad01e65d063213eb98ab7a3ededb2

---

## Common Errors

| Error | Fix |
|---|---|
| `ModuleNotFoundError` | Activate venv: `.\venv\Scripts\activate` |
<<<<<<< HEAD
| Groq `413` / `rate_limit_exceeded` | Request too large for free tier — retry; Gmail/Calendar use REST APIs to avoid oversized MCP tool schemas |
| `Connection refused` on WebSocket | Start backend: `python -m uvicorn api.main:api --reload --port 8000` |
| Gmail `Insufficient Permission` | Add `gmail.modify` on OAuth consent screen, delete `token.json`, re-run `auth_setup.py` |
| Calendar/Gmail not connected | Run OAuth setup; agents degrade gracefully with instructions |
=======
| Groq `413 / rate_limit_exceeded` | Request too large for free tier — retry; Gmail/Calendar use REST APIs to avoid oversized MCP schemas |
| `Connection refused` on WebSocket | Start backend: `python -m uvicorn api.main:api --reload --port 8000` |
| Gmail `Insufficient Permission` | Add `gmail.modify` scope, delete `token.json`, re-run `auth_setup.py` |
| Calendar/Gmail not responding | Run OAuth setup; agents degrade gracefully with setup instructions |
>>>>>>> 4eeae70feaaad01e65d063213eb98ab7a3ededb2
| Stale backend after code changes | Kill all processes on port 8000 and restart uvicorn |

---

<<<<<<< HEAD
*Built by Hamza Zeeshan — FAST NUCES Islamabad, Class of 2029*

*Stack: LangGraph · Groq · ChromaDB · Google APIs · FastAPI · React*
=======
## Live Demo

🔗 [atlas-ai.up.railway.app](https://atlas-ai.up.railway.app) ← *add your Railway URL here*

---

<div align="center">

Built by **Hamza Zeeshan** — FAST NUCES Islamabad, Class of 2029

*LangGraph · Groq · ChromaDB · MCP · FastAPI · React*

</div>
>>>>>>> 4eeae70feaaad01e65d063213eb98ab7a3ededb2
