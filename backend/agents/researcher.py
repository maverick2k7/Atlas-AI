"""Researcher agent: web search via Tavily + RAG synthesis with Groq.

Searches the web for relevant information, combines it with any past
memory context, and uses an LLM to synthesise a clear, comprehensive answer.
The synthesis is saved back to ChromaDB for future retrieval.
"""

from langchain_core.messages import SystemMessage, HumanMessage
from tavily import TavilyClient
from graph.workflow import AgentState
from memory.chroma_store import save_memory
from config import settings
from llm import groq_llm, invoke_llm

SYSTEM_PROMPT = """\
You are the Researcher agent in Atlas. Your job is to synthesise clear, \
accurate, and well-structured answers from web search results and past context.

Guidelines:
- Combine information from multiple sources into a coherent response.
- Highlight key facts, findings, and developments.
- Be concise but thorough — aim for a useful, readable summary.
- If past context is relevant, incorporate it naturally.
- Structure your response with clear paragraphs or bullet points as appropriate.
- Do NOT fabricate information — only use what is provided in the sources."""


def researcher_node(state: AgentState) -> dict:
    """Researcher node: search → combine → synthesise → save to memory.

    1. Calls Tavily search API (max 5 results)
    2. Combines web results with memory_context from supervisor
    3. Calls LLM to synthesise a clear answer
    4. Saves the synthesis to ChromaDB
    5. Returns state with results["research"] filled
    """
    task = state["task"]
    memory_context = state.get("memory_context", [])

    # --- Step 1: Web search via Tavily ---
    print(f"  [Researcher] Searching web for: {task}")
    tavily = TavilyClient(api_key=settings.tavily_api_key)
    search_results = tavily.search(query=task, max_results=5)

    # Format search results for the LLM
    sources = []
    for i, result in enumerate(search_results.get("results", []), 1):
        sources.append(
            f"Source {i}: {result.get('title', 'Untitled')}\n"
            f"URL: {result.get('url', '')}\n"
            f"Content: {result.get('content', '')}"
        )
    sources_text = "\n\n---\n\n".join(sources) if sources else "(No results found)"

    # Format memory context
    memory_text = ""
    if memory_context:
        memory_text = (
            "\n\nRelevant past context from memory:\n"
            + "\n".join(f"- {m}" for m in memory_context)
        )

    # --- Step 2: Synthesise with LLM ---
    print(f"  [Researcher] Synthesising {len(sources)} sources...")
    llm = groq_llm()

    human_content = (
        f"Task: {task}\n\n"
        f"Web search results:\n{sources_text}"
        f"{memory_text}\n\n"
        f"Synthesise a clear, comprehensive answer from the above sources."
    )

    response = invoke_llm(llm, [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=human_content),
    ])

    raw = response.content
    if isinstance(raw, list):
        raw = " ".join(
            part.get("text", "") if isinstance(part, dict) else str(part)
            for part in raw
        )
    synthesis = str(raw)

    # --- Step 3: Save to memory ---
    save_memory(synthesis, {"agent": "researcher", "task": task})
    print(f"  [Researcher] Done — saved {len(synthesis)} chars to memory.")

    return {
        "results": {"research": synthesis},
        "active_agent": "researcher",
    }
