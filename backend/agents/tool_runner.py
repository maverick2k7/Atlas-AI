"""Run an LLM with bound MCP tools — executes tool calls in a loop."""

import asyncio

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from llm import groq_llm, invoke_llm

_MAX_TOOL_RESULT_CHARS = 4000


def _truncate(text: str) -> str:
    if len(text) <= _MAX_TOOL_RESULT_CHARS:
        return text
    return text[:_MAX_TOOL_RESULT_CHARS] + "\n...(truncated for token limit)"


async def _ainvoke_tool(tool, args: dict) -> object:
    """Invoke an MCP tool asynchronously (MCP tools reject sync invoke)."""
    return await tool.ainvoke(args)


def _run_tool(tool, args: dict) -> object:
    """Run an async MCP tool from sync agent code."""
    try:
        return asyncio.run(_ainvoke_tool(tool, args))
    except RuntimeError:
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, _ainvoke_tool(tool, args))
            return future.result()


def invoke_llm_with_tools(llm_with_tools, messages: list, tools: list, *, max_rounds: int = 5):
    """Invoke LLM, execute any tool calls, repeat until the model returns text.

    Returns (response, all_messages) where all_messages includes tool outputs.
    """
    tool_map = {t.name: t for t in tools}
    messages = list(messages)
    response = invoke_llm(llm_with_tools, messages)

    for _ in range(max_rounds):
        tool_calls = getattr(response, "tool_calls", None) or []
        if not tool_calls:
            break

        messages = list(messages) + [response]
        for tc in tool_calls:
            name = tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", "")
            args = tc.get("args", {}) if isinstance(tc, dict) else getattr(tc, "args", {})
            tool_call_id = tc.get("id", "") if isinstance(tc, dict) else getattr(tc, "id", "")

            tool = tool_map.get(name)
            if tool is None:
                result = f"Unknown tool: {name}"
            else:
                try:
                    result = _run_tool(tool, args)
                except Exception as exc:
                    result = f"Tool error ({name}): {exc}"

            messages.append(
                ToolMessage(content=_truncate(str(result)), tool_call_id=tool_call_id)
            )

        response = invoke_llm(llm_with_tools, messages)

    # Groq small models sometimes finish with tool calls but no text — synthesise one.
    content = response.content
    if isinstance(content, list):
        content = " ".join(
            part.get("text", "") if isinstance(part, dict) else str(part)
            for part in content
        )
    if not str(content).strip():
        tool_outputs = [
            m.content for m in messages if isinstance(m, ToolMessage) and m.content
        ]
        if tool_outputs:
            final = invoke_llm(
                groq_llm(max_tokens=512),
                [
                    SystemMessage(content=(
                        "You are a helpful assistant. Summarise the tool results below "
                        "into a clear, concise answer for the user."
                    )),
                    HumanMessage(content="\n\n---\n\n".join(tool_outputs)),
                ],
            )
            return final, messages

    return response, messages


def tool_outputs_indicate_mcp_failure(messages: list) -> bool:
    """True when MCP tool results show auth/API setup errors."""
    markers = (
        "does not have permission",
        "does not support sync invocation",
        "has not been used in project",
        "is disabled",
        "asynchronously",
        "documentation on how to use",
    )
    for msg in messages:
        if isinstance(msg, ToolMessage) and any(m in str(msg.content) for m in markers):
            return True
    return False
