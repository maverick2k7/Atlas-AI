"""Writer agent: drafts, edits, and summarises text using Groq.

Pure LLM node — no external tool calls. If researcher already ran in this
pipeline (results["research"] is populated), its findings are included in
the prompt so the writer can build on them naturally.
"""

from langchain_core.messages import SystemMessage, HumanMessage
from graph.workflow import AgentState
from memory.chroma_store import save_memory
from llm import groq_llm, invoke_llm

SYSTEM_PROMPT = """\
You are an expert writer inside Atlas — Autonomous Task & Learning Agent System.

Your job is to draft, edit, or summarise text as requested by the user.

Guidelines:
- Only produce written content when the user explicitly asks you to write, draft, \
or edit something.
- If the task is vague, a greeting, or not a writing request, reply in one or two \
sentences asking what they would like you to write — do NOT invent an email or document.
- Ignore past memory context unless it is clearly relevant to the current task.
- Be concise and professional.
- Match the tone requested (formal, casual, persuasive, etc.).
- If research findings are provided, incorporate them naturally into your writing.
- Do NOT add meta-commentary like "Here is the email:" — just produce the content."""


def writer_node(state: AgentState) -> dict:
    """Writer node: draft or edit text, optionally using researcher results.

    1. Checks if research results are available from a previous node
    2. Builds a prompt combining the task + any research context
    3. Calls LLM to produce the written output
    4. Saves the draft to ChromaDB memory
    5. Returns state with results["writing"] filled
    """
    task = state["task"]
    memory_context = state.get("memory_context", [])
    research = state.get("results", {}).get("research", "")

    # --- Build context blocks ---
    research_block = ""
    if research:
        research_block = (
            "\n\nResearch findings available (incorporate as relevant):\n"
            f"{research}"
        )

    memory_block = ""
    if memory_context:
        memory_block = (
            "\n\nRelevant past context from memory:\n"
            + "\n".join(f"- {m}" for m in memory_context)
        )

    human_content = (
        f"Task: {task}"
        f"{research_block}"
        f"{memory_block}\n\n"
        f"Complete the writing task above."
    )

    # --- Call LLM ---
    print(f"  [Writer] Drafting response for: {task}")
    llm = groq_llm()

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
    draft = str(raw)

    # --- Save to memory ---
    save_memory(draft, {"agent": "writer", "task": task})
    print(f"  [Writer] Done — saved {len(draft)} chars to memory.")

    return {
        "results": {"writing": draft},
        "active_agent": "writer",
    }
