"""Shared Groq LLM factory — keeps token limits consistent across agents."""

import time

from groq import APIStatusError, RateLimitError
from langchain_groq import ChatGroq
from config import settings

MODEL = "llama-3.1-8b-instant"


def groq_llm(*, max_tokens: int = 768) -> ChatGroq:
    """Return a ChatGroq instance with sensible defaults for Atlas."""
    return ChatGroq(
        model=MODEL,
        api_key=settings.groq_api_key,
        temperature=0.1,
        max_tokens=max_tokens,
    )


def invoke_llm(llm: ChatGroq, messages: list, *, retries: int = 3) -> object:
    """Invoke Groq with automatic backoff on free-tier rate limits."""
    for attempt in range(retries):
        try:
            return llm.invoke(messages)
        except (RateLimitError, APIStatusError) as exc:
            if attempt == retries - 1:
                raise
            # Back off on TPM / oversized-request errors from Groq free tier
            if getattr(exc, "status_code", None) not in (413, 429, None):
                raise
            time.sleep(12 * (attempt + 1))
