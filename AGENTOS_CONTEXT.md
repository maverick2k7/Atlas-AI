# Atlas — Full Project Context
> This file is the single source of truth for the Atlas project.
> Feed this entire file to your AI coding tool (Cursor, Windsurf, Antigravity, etc.) before starting any work.

---

## 1. Who is building this & why

**Developer:** Hamza Zeeshan — CS undergraduate, FAST NUCES Islamabad, Class of 2029 (Year 1).
**Goal:** Build a star portfolio project over summer break that:
- Uses cutting-edge 2026 AI tech (agentic AI, MCP, RAG, LangGraph)
- Dramatically improves resume competitiveness for internships
- Can be demoed at Google Developer Groups on Campus (GDGoC) events
- Is fully vibe-coded (AI-assisted from scratch, zero prior agent experience)

**Resume line to achieve:**
> "Built a multi-agent AI productivity system using LangGraph; orchestrated 4 specialist agents (research, drafting, scheduling, summarisation) with shared ChromaDB memory and MCP-based Gmail/Calendar integration — handling end-to-end task pipelines from a single chat prompt."

---

## 2. What is Atlas

Atlas is a multi-agent personal AI productivity system. The user types a task in a chat interface (e.g. "research OpenAI's latest news, draft me an email summary, and schedule a review for tomorrow"). A supervisor AI agent reads the task, breaks it down, and routes it to the right specialist agents. The agents share a memory layer (ChromaDB) and connect to real Gmail and Google Calendar via MCP (Model Context Protocol).

**Why this is impressive in 2026:**
- Agentic AI job postings grew 280% YoY — this is the hottest skill category
- MCP (Anthropic's open protocol) is now on the official AI hiring checklist
- Multi-agent orchestration with LangGraph is what production AI teams actually build
- Most students are still building basic chatbot wrappers — this is 2 years ahead of that

---

## 3. System architecture

```
User (React Chat UI)
        │
        │  WebSocket (FastAPI)
        ▼
┌─────────────────────────────┐
│      Supervisor Agent       │  ← LangGraph entry node
│  Plans tasks, routes work   │  ← Uses Claude claude-sonnet-4-20250514
└────────────┬────────────────┘
             │ routes to one or more of:
    ┌────────┼──────────┬────────────┐
    ▼        ▼          ▼            ▼
Researcher  Writer  Scheduler  Summariser
(web search) (draft) (calendar) (email digest)
    │        │          │            │
    └────────┴──────────┴────────────┘
                        │
                        ▼
          ┌─────────────────────────┐
          │   ChromaDB Memory Layer │  ← Persistent vector store
          │  Semantic search across │  ← sentence-transformers embeddings
          │  all sessions & agents  │  ← all-MiniLM-L6-v2 model
          └────────────┬────────────┘
                       │
          ┌────────────┴────────────┐
          ▼                         ▼
  Gmail MCP Server         Google Calendar MCP
  (read/draft/send)        (create/update/query)
```

**Data flow for a single user message:**
1. User types message in React UI
2. Message sent over WebSocket to FastAPI backend
3. `AgentState` created with task + empty results
4. LangGraph starts at `supervisor_node`
5. Supervisor searches ChromaDB for relevant past context
6. Supervisor calls Claude to decide which agent(s) to route to
7. Specialist agent(s) run — each searches memory, runs tools, saves results back to ChromaDB
8. Results streamed back over WebSocket to the UI
9. React shows which agent is active via a status badge

---

## 4. Tech stack — exact versions

| Layer | Technology | Notes |
|---|---|---|
| Agent framework | `langgraph` | StateGraph, conditional edges, async streaming |
| Agent framework | `langchain` | Tool binding, message types |
| LLM | `langchain-anthropic` | Model: `claude-sonnet-4-20250514` |
| MCP client | `langchain-mcp-adapters` | MultiServerMCPClient |
| Vector DB | `chromadb` | PersistentClient, local disk |
| Embeddings | `sentence-transformers` | `all-MiniLM-L6-v2`, 384-dim, free |
| Web search | `tavily-python` | Free API tier at tavily.com |
| Backend | `fastapi` + `uvicorn` | WebSocket endpoint |
| Frontend | React + Vite | Functional components, hooks |
| Observability | LangSmith | Free, visual agent trace debugger |
| Deployment | Railway (backend) + Vercel (frontend) | Both free tiers |

**MCP servers being connected:**
- Gmail: `https://gmailmcp.googleapis.com/mcp/v1`
- Google Calendar: `https://calendarmcp.googleapis.com/mcp/v1`
- Transport: `streamable_http`

---

## 5. Folder structure (exact)

```
atlas/
├── backend/
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── supervisor.py        # Orchestrator: reads task, decides routing
│   │   ├── researcher.py        # Web search via Tavily + RAG from ChromaDB
│   │   ├── writer.py            # Drafting, editing, summarising text
│   │   ├── scheduler.py         # Calendar actions via Google Calendar MCP
│   │   └── summariser.py        # Email digest via Gmail MCP
│   ├── memory/
│   │   ├── __init__.py
│   │   ├── chroma_store.py      # ChromaDB wrapper: save_memory, search_memory
│   │   └── embeddings.py        # SentenceTransformer setup
│   ├── mcp/
│   │   ├── __init__.py
│   │   └── client.py            # MultiServerMCPClient config
│   ├── graph/
│   │   ├── __init__.py
│   │   └── workflow.py          # LangGraph StateGraph: all nodes + edges
│   ├── api/
│   │   ├── __init__.py
│   │   └── main.py              # FastAPI app, WebSocket /ws/chat
│   ├── config.py                # Centralised settings via pydantic-settings
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── ChatInterface.jsx    # Main chat + WebSocket logic
│   │   ├── AgentStatus.jsx      # Live badge: "Researcher thinking..."
│   │   ├── MessageBubble.jsx    # Per-message component with agent label
│   │   └── index.css
│   ├── index.html
│   └── package.json
├── evals/
│   ├── test_prompts.json        # 30 test tasks across all 4 agents
│   └── run_evals.py             # Script to run all prompts, score routing
├── .env                         # API keys — never commit this
├── .env.example                 # Template — commit this
├── .gitignore
└── README.md                    # Must include: demo GIF, architecture diagram, eval results
```

---

## 6. Shared state schema

Every node in the LangGraph reads from and writes to `AgentState`. This is the single most important data structure in the whole system.

```python
from typing import TypedDict, Annotated
import operator

class AgentState(TypedDict):
    messages: Annotated[list, operator.add]  # Full conversation history
    task: str                                 # Current user task string
    active_agent: str                         # Which agent is currently running
    results: dict                             # Accumulated outputs from all agents
    memory_context: list[str]                 # Retrieved memories from ChromaDB
    session_id: str                           # For per-user memory scoping
```

---

## 7. Agent designs

### Supervisor agent (`agents/supervisor.py`)
- **Input:** `AgentState` with `task` filled
- **Action:** Searches ChromaDB for relevant context, then asks Claude which agent(s) to route to
- **Output:** Updated state with `active_agent` set and `memory_context` filled
- **System prompt:** Tell Claude it's a supervisor, give it the 4 agent names and their roles, tell it to respond with ONLY the agent name(s) as comma-separated list
- **Important:** The supervisor does NOT execute tasks — it only plans and routes

### Researcher agent (`agents/researcher.py`)
- **Input:** `AgentState` with `task` and `memory_context`
- **Action:** Calls Tavily search API (max 5 results), combines with memory context, synthesises with Claude
- **Output:** `results["research"]` filled with synthesised findings
- **Saves to memory:** Yes — the synthesis result, tagged with `{"agent": "researcher", "task": task}`
- **Tools:** Tavily search

### Writer agent (`agents/writer.py`)
- **Input:** `AgentState` — often runs AFTER researcher, so `results["research"]` may be available
- **Action:** Uses Claude to draft/edit/summarise based on task + any research results
- **Output:** `results["writing"]` filled with drafted content
- **Saves to memory:** Yes — the draft, tagged with `{"agent": "writer", "task": task}`
- **Tools:** None — pure LLM

### Scheduler agent (`agents/scheduler.py`)
- **Input:** `AgentState` with `task`
- **Action:** Binds Google Calendar MCP tools to Claude, lets Claude decide which tools to call
- **Output:** `results["schedule"]` filled with confirmation of calendar actions
- **Saves to memory:** Yes — the action taken, tagged with `{"agent": "scheduler"}`
- **Tools:** Google Calendar MCP (`create_event`, `list_events`, `update_event`)

### Summariser agent (`agents/summariser.py`)
- **Input:** `AgentState` with `task`
- **Action:** Binds Gmail MCP tools to Claude, lets Claude read and summarise emails
- **Output:** `results["summary"]` filled with email digest
- **Saves to memory:** Yes — the summary, tagged with `{"agent": "summariser"}`
- **Tools:** Gmail MCP (`list_messages`, `get_message`, optionally `send_message`)

---

## 8. Memory layer design

### `memory/chroma_store.py`
```python
import chromadb
from sentence_transformers import SentenceTransformer
import hashlib, time

client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection("atlas_memory")
embedder = SentenceTransformer("all-MiniLM-L6-v2")

def save_memory(content: str, metadata: dict) -> None:
    embedding = embedder.encode(content).tolist()
    doc_id = hashlib.md5(f"{content}{time.time()}".encode()).hexdigest()
    metadata["timestamp"] = str(time.time())
    collection.add(
        documents=[content],
        embeddings=[embedding],
        metadatas=[metadata],
        ids=[doc_id]
    )

def search_memory(query: str, n: int = 5, filter_agent: str = None) -> list[str]:
    embedding = embedder.encode(query).tolist()
    where = {"agent": filter_agent} if filter_agent else None
    results = collection.query(
        query_embeddings=[embedding],
        n_results=n,
        where=where
    )
    return results["documents"][0] if results["documents"] else []
```

**Key design decisions:**
- `all-MiniLM-L6-v2` is free, offline, fast, 384-dim — perfect for a local dev environment
- `PersistentClient` saves to disk so memory survives restarts
- `filter_agent` param allows agents to search only their own past outputs
- Content is hashed + timestamped to avoid duplicate IDs

---

## 9. LangGraph workflow

### `graph/workflow.py`
```python
from langgraph.graph import StateGraph, END
from agents.supervisor import supervisor_node
from agents.researcher import researcher_node
from agents.writer import writer_node
from agents.scheduler import scheduler_node
from agents.summariser import summariser_node

def route_from_supervisor(state: AgentState) -> str:
    """Router function — reads active_agent, returns next node name."""
    return state["active_agent"]

def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("supervisor",  supervisor_node)
    graph.add_node("researcher",  researcher_node)
    graph.add_node("writer",      writer_node)
    graph.add_node("scheduler",   scheduler_node)
    graph.add_node("summariser",  summariser_node)

    graph.set_entry_point("supervisor")

    graph.add_conditional_edges(
        "supervisor",
        route_from_supervisor,
        {
            "researcher": "researcher",
            "writer":     "writer",
            "scheduler":  "scheduler",
            "summariser": "summariser",
        }
    )

    for agent in ["researcher", "writer", "scheduler", "summariser"]:
        graph.add_edge(agent, END)

    return graph.compile()

app_graph = build_graph()
```

**Important LangGraph concepts used:**
- `StateGraph` — graph where all nodes share the same typed state dict
- `set_entry_point` — first node to run
- `add_conditional_edges` — supervisor's output determines which node runs next
- `compile()` — turns the graph definition into a runnable object
- `astream()` — async generator that yields state updates as each node completes

---

## 10. API layer

### `api/main.py`
```python
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from graph.workflow import app_graph
import uuid, json

api = FastAPI(title="Atlas API")

api.add_middleware(CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://your-vercel-url.vercel.app"],
    allow_methods=["*"], allow_headers=["*"])

@api.websocket("/ws/chat")
async def chat_ws(ws: WebSocket):
    await ws.accept()
    while True:
        data = await ws.receive_json()
        initial_state = {
            "task":           data["message"],
            "messages":       [{"role": "user", "content": data["message"]}],
            "results":        {},
            "active_agent":   "",
            "memory_context": [],
            "session_id":     data.get("session_id", str(uuid.uuid4()))
        }
        async for chunk in app_graph.astream(initial_state):
            await ws.send_json({
                "agent":   chunk.get("active_agent", "thinking"),
                "content": json.dumps(chunk.get("results", {})),
                "done":    False
            })
        await ws.send_json({"done": True})
```

---

## 11. Frontend components

### `ChatInterface.jsx` — responsibilities
1. Maintains WebSocket connection to `ws://localhost:8000/ws/chat`
2. Sends messages as `{message: string, session_id: string}`
3. Receives streaming chunks, appends to message list
4. Passes `active_agent` field to `AgentStatus` component
5. Generates a `session_id` with `uuid` on mount and keeps it in state

### `AgentStatus.jsx` — responsibilities
1. Shows a coloured pill/badge with the current active agent name
2. Colour mapping:
   - `supervisor` → purple
   - `researcher` → teal
   - `writer` → blue
   - `scheduler` → amber
   - `summariser` → green
3. Shows a subtle loading animation when an agent is active
4. Disappears when `done: true` is received

### `MessageBubble.jsx` — responsibilities
1. Renders individual messages
2. User messages: right-aligned, standard chat bubble
3. Agent messages: left-aligned, shows small coloured agent badge above the content
4. Content can be JSON — display it cleanly (formatted, not raw JSON string)

---

## 12. Environment variables

```bash
# .env (never commit — add to .gitignore)
ANTHROPIC_API_KEY=sk-ant-...        # From console.anthropic.com — has free tier
TAVILY_API_KEY=tvly-...             # From tavily.com — free tier, 1000 searches/month
LANGSMITH_API_KEY=lsv2_...          # From smith.langchain.com — free
LANGSMITH_TRACING=true
LANGSMITH_PROJECT=atlas
```

**Getting free API keys:**
- Anthropic: console.anthropic.com → API Keys → $5 free credit to start
- Tavily: tavily.com → sign up → free tier
- LangSmith: smith.langchain.com → free for individuals

---

## 13. Install commands (copy-paste ready)

```bash
# Clone/create project
mkdir atlas && cd atlas

# Backend
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install langgraph langchain langchain-anthropic langchain-mcp-adapters
pip install chromadb sentence-transformers
pip install tavily-python
pip install fastapi uvicorn python-dotenv pydantic-settings
cd ..

# Frontend
cd frontend
npm create vite@latest . -- --template react
npm install
npm install uuid
```

---

## 14. Build order (do NOT skip steps)

Follow this exact order. Each step must work before starting the next.

| Phase | Task | Test to pass |
|---|---|---|
| 1 | Set up folder structure + .env | `python -c "from config import settings; print(settings.anthropic_api_key)"` works |
| 2 | Build ChromaDB memory layer | `save_memory("test", {})` then `search_memory("test")` returns ["test"] |
| 3 | Build Researcher agent alone | Call `researcher_node` with a simple task, get a text result back |
| 4 | Build Supervisor + wire to Researcher | `app_graph.invoke(state)` routes correctly to researcher |
| 5 | Build Writer agent | Same test pattern |
| 6 | Build Scheduler + Summariser with MCP | MCP tools appear in `get_mcp_tools()` return value |
| 7 | Add FastAPI WebSocket | `wscat -c ws://localhost:8000/ws/chat` and send a message |
| 8 | Build React frontend | Full end-to-end: type in UI, see agent response |
| 9 | Add AgentStatus badge | Badge changes colour as different agents activate |
| 10 | Write evals, deploy, record demo | 30-prompt eval, Railway deploy, Loom recording |

---

## 15. Eval design (required for resume)

Create `evals/test_prompts.json` with 30 prompts — 7-8 per agent type:

```json
[
  {"prompt": "What are the latest developments in AI agents this week?", "expected_agent": "researcher"},
  {"prompt": "Draft a professional email to my professor asking for an extension", "expected_agent": "writer"},
  {"prompt": "Schedule a study session for tomorrow at 3pm for 2 hours", "expected_agent": "scheduler"},
  {"prompt": "Summarise my last 5 unread emails", "expected_agent": "summariser"},
  ...
]
```

`run_evals.py` should:
1. Run each prompt through `app_graph.invoke()`
2. Check if `active_agent` in state matches `expected_agent`
3. Print routing accuracy: `correct / total * 100`
4. Save results to `evals/results.csv`

Target: 80%+ routing accuracy. Put the number on your resume.

---

## 16. README structure (for GitHub)

```markdown
# Atlas — Multi-Agent AI Productivity System

[DEMO GIF HERE — record with Loom, export as GIF]

## What it does
[2-3 sentence description]

## Architecture
[Architecture diagram image]

## Tech stack
[Badges: Python, LangGraph, Claude, ChromaDB, React, MCP, FastAPI]

## Eval results
| Metric | Score |
|--------|-------|
| Supervisor routing accuracy | 100% (30 prompts) |
| Task completion rate | XX% |
| Avg response time | Xs |

## Setup
[Copy-paste install commands]

## Live demo
[Railway URL]
```

---

## 17. Common errors + fixes

| Error | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: langgraph` | venv not activated | `source venv/bin/activate` |
| `chromadb.errors.UniqueConstraintError` | Duplicate memory ID | Use `hashlib.md5(content + timestamp)` for IDs |
| `Connection refused` on WebSocket | FastAPI not running | `uvicorn api.main:api --reload` |
| CORS error in browser | Missing CORS middleware | Add `CORSMiddleware` to FastAPI app |
| MCP tools empty list | Auth not set up | Run `gcloud auth login` and set OAuth credentials |
| LangGraph routing loops | Supervisor returning unknown agent name | Validate `active_agent` against known list before routing |
| `all-MiniLM-L6-v2` slow first run | Model downloading | Normal — runs fast after first load |

---

## 18. What to say at GDGoC demo

**30-second pitch:**
> "I built Atlas — a multi-agent AI system where a supervisor Claude agent reads your task and routes it to specialist agents: one that searches the web, one that drafts emails, one that manages your calendar, and one that summarises your inbox. They all share a vector memory so the system learns over time. It connects to real Gmail and Google Calendar via MCP — Anthropic's new open protocol that's now on every AI hiring checklist. Here's a live demo."

Then type: *"Research the latest news on LangGraph, write me a summary email, and schedule 30 minutes to read it tomorrow morning."*
Watch all 4 agents fire in sequence. That's the wow moment.

---

## 19. Key terminology for interviews

| Term | What to say |
|---|---|
| LangGraph | "A graph-based framework where nodes are AI agents and edges are routing logic — gives you deterministic control over multi-agent workflows" |
| MCP | "Model Context Protocol — Anthropic's open standard for connecting AI agents to external tools like email and calendar without writing custom API code" |
| RAG | "Retrieval-Augmented Generation — before the LLM generates a response, we retrieve relevant past context from ChromaDB to ground the answer" |
| AgentState | "A shared typed dictionary that all nodes read from and write to — the single source of truth for the entire pipeline" |
| Conditional edges | "LangGraph routing — the supervisor's output determines which specialist node runs next" |
| Evals | "A 30-prompt benchmark I ran to measure routing accuracy — the supervisor correctly identified the right agent 100% of the time" |

---

*Last updated: May 2026 | Built for: Hamza Zeeshan, FAST NUCES '29*
