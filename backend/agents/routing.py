"""Lightweight routing helpers — greetings, pre-routing, and multi-agent planning."""

import re

CHITCHAT_REPLY = (
    "Hi! I'm Atlas — Autonomous Task & Learning Agent System.\n\n"
    "I can help you:\n"
    "• Research — look up news and facts on the web\n"
    "• Write — draft emails, reports, and documents\n"
    "• Schedule — manage your calendar (when connected)\n"
    "• Summarise — digest your inbox (when connected)\n\n"
    "What would you like to do?"
)

CREATOR_REPLY = "I was built by Hamza Zeeshan."

AGENT_PIPELINE_ORDER = ("researcher", "writer", "scheduler", "summariser")

_CHITCHAT_PHRASES = {
    "hi", "hello", "hey", "hiya", "yo", "sup", "howdy",
    "thanks", "thank you", "thx", "ok", "okay", "k",
    "bye", "goodbye", "see you", "cheers",
    "good morning", "good afternoon", "good evening",
}

_CREATOR_PHRASES = (
    "who made you",
    "who created you",
    "who built you",
    "who developed you",
    "who designed you",
    "who is your creator",
    "who is your developer",
    "who made atlas",
    "who built atlas",
    "who created atlas",
)

_GMAIL_ACCOUNT_SIGNALS = (
    "my email", "my emails", "my inbox", "unread",
    "latest email", "last email", "recent email",
    "urgent email", "urgent emails",
    "emails i need", "emails from", "emails about", "emails i received",
    "emails did i receive", "what emails",
    "digest of my inbox", "digest of my email",
    "mark as read", "mark read", "archive", "gmail",
    "reply to my", "reply to the latest", "reply to latest",
    "send an email to", "send email to", "save to gmail", "gmail draft",
)

_SCHEDULER_SIGNALS = (
    "schedule", "calendar", "meeting", "appointment", "book a slot",
    "availability", "free busy", "free/busy", "block out", "am i free",
)

_RESEARCH_SIGNALS = (
    "research", "look up", "lookup", "find out", "search for",
    "latest news", "what is happening", "tell me about",
    "what are the latest", "what is the latest", "developments in",
    "newest model", "benchmarks comparing", "find information",
)

_WRITING_VERBS = ("draft", "write", "compose", "rewrite", "edit", "proofread", "summaris", "summariz")
_WRITING_NOUNS = (
    "email", "letter", "report", "document", "essay", "memo", "proposal",
    "paragraph", "message", "readme", "summary", "cover letter", "linkedin",
)


def is_chitchat(message: str) -> bool:
    """True for greetings and other messages with no real task."""
    normalized = message.strip().lower().rstrip("!?.,")
    if not normalized:
        return False
    if normalized in _CHITCHAT_PHRASES:
        return True
    words = normalized.split()
    if len(words) <= 3 and words[0] in _CHITCHAT_PHRASES:
        return True
    return False


def is_creator_question(message: str) -> bool:
    """True when the user asks who built Atlas."""
    normalized = message.strip().lower().rstrip("!?.,")
    return any(phrase in normalized for phrase in _CREATOR_PHRASES)


def get_direct_reply(message: str) -> str | None:
    """Return a canned reply for meta questions, or None to run the agent graph."""
    if is_chitchat(message):
        return CHITCHAT_REPLY
    if is_creator_question(message):
        return CREATOR_REPLY
    return None


def is_gmail_account_task(message: str) -> bool:
    """True when the user wants to read or change their actual Gmail mailbox."""
    normalized = message.strip().lower()

    if re.search(
        r"summari[sz]e this (?:research paper|paper|article|document|text|paragraph)",
        normalized,
    ):
        return False
    if re.search(r"summari[sz]e .+ bullet points", normalized) and not re.search(
        r"\b(?:email|mail|inbox)\b", normalized
    ):
        return False

    if any(signal in normalized for signal in _GMAIL_ACCOUNT_SIGNALS):
        return True
    if re.search(r"summari[sz]e", normalized) and re.search(
        r"\b(?:email|mail|inbox|unread)\b", normalized
    ):
        return True
    if re.search(r"\b(?:show me|check|read)\b.*\b(?:email|mail|inbox)\b", normalized):
        return True
    if re.search(r"\bsend (?:an )?email to \S+@", normalized):
        return True
    if re.search(r"\breply to \S+@", normalized):
        return True
    return False


def is_writer_composition_task(message: str) -> bool:
    """True when the user wants text written, not Gmail account actions."""
    normalized = message.strip().lower()
    if is_gmail_account_task(message):
        return False

    if re.search(
        r"summari[sz]e this (?:research paper|paper|article|document|text|paragraph)",
        normalized,
    ):
        return True
    if re.search(r"summari[sz]e .+ in \d+ bullet points", normalized):
        return True

    has_verb = any(verb in normalized for verb in _WRITING_VERBS)
    has_noun = any(noun in normalized for noun in _WRITING_NOUNS)
    return has_verb and has_noun


def has_research_intent(message: str) -> bool:
    normalized = message.strip().lower()

    if re.search(
        r"summari[sz]e this (?:research paper|paper|article|document|text|paragraph)",
        normalized,
    ):
        return False

    if any(signal in normalized for signal in _RESEARCH_SIGNALS):
        return True
    if re.search(r"\bresearch\b", normalized):
        return True
    if re.search(
        r"\b(?:what are|what is|what's|how does|how do|find the|what .+ (?:are|is))\b",
        normalized,
    ):
        if not (
            is_gmail_account_task(message)
            or any(s in normalized for s in _SCHEDULER_SIGNALS)
        ):
            return True
    return False


def has_writer_intent(message: str) -> bool:
    if is_writer_composition_task(message):
        return True
    normalized = message.strip().lower()
    if re.search(r"\b(?:write|draft|compose)\b.*\b(?:email|summary|report|letter)\b", normalized):
        return not is_gmail_account_task(message)
    return False


def has_scheduler_intent(message: str) -> bool:
    normalized = message.strip().lower()
    return any(signal in normalized for signal in _SCHEDULER_SIGNALS)


def infer_agent_route(message: str) -> str | None:
    """Return a single specialist agent for clear-cut tasks, or None for LLM fallback."""
    normalized = message.strip().lower()
    if not normalized:
        return None

    if is_writer_composition_task(message):
        return "writer"
    if is_gmail_account_task(message):
        return "summariser"
    if has_scheduler_intent(message):
        return "scheduler"
    if has_research_intent(message):
        return "researcher"

    return None


def _first_keyword_position(normalized: str, keywords: tuple[str, ...]) -> int | None:
    positions = [normalized.find(kw) for kw in keywords if kw in normalized]
    return min(positions) if positions else None


def _agent_keyword_groups() -> dict[str, tuple[str, ...]]:
    return {
        "researcher": _RESEARCH_SIGNALS + (
            "what are", "what is", "find information", "look up", "search for",
        ),
        "writer": _WRITING_VERBS + ("summary email", "short report", "cover letter"),
        "scheduler": _SCHEDULER_SIGNALS,
        "summariser": _GMAIL_ACCOUNT_SIGNALS + (
            "summarise", "summarize", "unread", "inbox", "my email",
        ),
    }


def infer_multi_agent_plan(message: str) -> list[str] | None:
    """Return an ordered multi-agent pipeline when the task spans 2+ domains."""
    intents: set[str] = set()
    if has_research_intent(message):
        intents.add("researcher")
    if has_writer_intent(message):
        intents.add("writer")
    if has_scheduler_intent(message):
        intents.add("scheduler")
    if is_gmail_account_task(message):
        intents.add("summariser")

    if len(intents) < 2:
        return None

    normalized = message.strip().lower()
    keywords = _agent_keyword_groups()
    ordered: list[tuple[int, str]] = []

    for agent in AGENT_PIPELINE_ORDER:
        if agent not in intents:
            continue
        pos = _first_keyword_position(normalized, keywords[agent])
        ordered.append((pos if pos is not None else 9999, agent))

    ordered.sort(key=lambda item: (item[0], AGENT_PIPELINE_ORDER.index(item[1])))
    return [agent for _, agent in ordered]


def plan_agents(message: str) -> list[str]:
    """Deterministic agent plan for a task (one or more agents in pipeline order)."""
    multi = infer_multi_agent_plan(message)
    if multi:
        return multi

    single = infer_agent_route(message)
    if single:
        return [single]

    return []
