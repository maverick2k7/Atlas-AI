"""Direct Gmail API access — read, send, draft, reply, and modify messages."""

from __future__ import annotations

import base64
import json
import re
from email.mime.text import MIMEText
from email.utils import parseaddr
from typing import Any

from googleapiclient.discovery import build
from langchain_core.messages import HumanMessage, SystemMessage

from llm import groq_llm, invoke_llm
from mcp_servers.client import get_oauth_credentials

SUMMARISE_PROMPT = """\
You are the Summariser agent in Atlas. Summarise ONLY the email(s) provided below.

Match the user's request exactly — if they asked for one email, summarise one email only.
For each email include: sender, subject, key point, and any action required.
Keep it brief — one or two sentences per email unless asked otherwise.
Flag anything urgent."""

_INTENT_PROMPT = """\
You parse Gmail task requests into JSON. Reply with ONLY a JSON object, no markdown.

Fields:
- action: one of summarise, send, draft, reply, mark_read, archive, delete, add_label, remove_label
- query: Gmail search query to find target email(s), e.g. "is:unread", "in:inbox", "from:alice@example.com"
- limit: how many matching emails to affect (default 1 for reply/delete/archive/mark_read, 5 for summarise)
- to: recipient email (for send/draft)
- subject: email subject (for send/draft; for reply use "Re: ..." when appropriate)
- body: email body text (for send/draft/reply — write a sensible message from the user's request)
- label: label name for add_label/remove_label (e.g. "IMPORTANT", "Work")

Rules:
- Use action "summarise" for read/digest/summary requests.
- Use action "send" when the user wants to send an email now.
- Use action "draft" when the user wants to save a draft without sending.
- Use action "reply" when replying to an existing email; set limit to 1 and query to find that email.
- Use mark_read, archive, delete, add_label, remove_label for inbox management.
- For "latest/last email" use query "in:inbox" and limit 1.
- For unread summaries use query "is:unread".
- Always provide body text for send/draft/reply actions."""

_WORD_NUMBERS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}


def _gmail_service():
    creds = get_oauth_credentials()
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def _extract_json(text: str) -> dict:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise ValueError(f"Could not parse Gmail intent: {text[:200]}")


def _llm_text(response) -> str:
    raw = response.content
    if isinstance(raw, list):
        raw = " ".join(
            part.get("text", "") if isinstance(part, dict) else str(part)
            for part in raw
        )
    return str(raw)


def _header_map(payload: dict) -> dict[str, str]:
    return {h["name"]: h["value"] for h in payload.get("headers", [])}


def _snippet_from_payload(payload: dict) -> str:
    if payload.get("body", {}).get("data"):
        try:
            raw = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")
            return re.sub(r"\s+", " ", raw).strip()[:500]
        except Exception:
            pass
    for part in payload.get("parts", []) or []:
        if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
            try:
                raw = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
                return re.sub(r"\s+", " ", raw).strip()[:500]
            except Exception:
                continue
    return ""


def _parse_limit(task: str, default: int = 5) -> int:
    lowered = task.lower()
    match = re.search(r"\b(?:last|latest|recent|top|first)\s+(\d+)\b", lowered)
    if match:
        return max(1, min(int(match.group(1)), 20))
    match = re.search(r"\b(\d+)\s+(?:unread\s+)?(?:email|emails|message|messages|mail)\b", lowered)
    if match:
        return max(1, min(int(match.group(1)), 20))
    for word, num in _WORD_NUMBERS.items():
        if re.search(rf"\b(?:last|latest|recent|top|first)\s+{word}\b", lowered):
            return num
        if re.search(rf"\b{word}\s+(?:unread\s+)?(?:email|emails|message|messages|mail)\b", lowered):
            return num
    singular_patterns = (
        r"\b(?:latest|last|most recent|newest)\s+(?:email|message|mail)\b",
        r"\b(?:summari[sz]e|read|check|show|reply to|archive|delete|mark)\s+(?:my\s+)?(?:the\s+)?(?:latest|last|most recent|newest)\b",
        r"\b(?:an?\s+email|one\s+email|single\s+email)\b",
    )
    if any(re.search(pat, lowered) for pat in singular_patterns):
        return 1
    if re.search(r"\b(?:email|message|mail)\b", lowered) and not re.search(
        r"\b(?:email|message|mail)s\b", lowered
    ):
        return 1
    match = re.search(r"\b(\d+)\b", lowered)
    if match and any(w in lowered for w in ("email", "message", "mail", "unread", "inbox")):
        return max(1, min(int(match.group(1)), 20))
    return default


def _parse_query(task: str) -> str:
    lowered = task.lower()
    if "unread" in lowered:
        return "is:unread"
    if "inbox" in lowered:
        return "in:inbox"
    if any(w in lowered for w in ("latest", "last", "recent", "newest")):
        return "in:inbox"
    return "in:inbox"


def parse_gmail_intent(task: str) -> dict:
    """Use the LLM to classify a Gmail request and extract structured fields."""
    response = invoke_llm(
        groq_llm(max_tokens=384),
        [
            SystemMessage(content=_INTENT_PROMPT),
            HumanMessage(content=task),
        ],
    )
    intent = _extract_json(_llm_text(response))
    intent.setdefault("action", "summarise")
    intent.setdefault("query", _parse_query(task))
    intent.setdefault("limit", _parse_limit(task, default=1 if intent["action"] != "summarise" else 5))
    return intent


def _message_to_dict(msg: dict) -> dict[str, Any]:
    headers = _header_map(msg.get("payload", {}))
    sender_name, sender_email = parseaddr(headers.get("From", ""))
    return {
        "id": msg["id"],
        "thread_id": msg.get("threadId", ""),
        "from": sender_name or sender_email or headers.get("From", "Unknown"),
        "from_email": sender_email or headers.get("From", ""),
        "to": headers.get("To", ""),
        "subject": headers.get("Subject", "(no subject)"),
        "date": headers.get("Date", ""),
        "message_id": headers.get("Message-ID", headers.get("Message-Id", "")),
        "references": headers.get("References", ""),
        "snippet": msg.get("snippet") or _snippet_from_payload(msg.get("payload", {})),
        "label_ids": msg.get("labelIds", []),
    }


def _list_message_ids(*, query: str, limit: int) -> list[str]:
    service = _gmail_service()
    listed = (
        service.users()
        .messages()
        .list(userId="me", q=query, maxResults=limit)
        .execute()
    )
    return [ref["id"] for ref in listed.get("messages", [])]


def _get_message(message_id: str) -> dict:
    service = _gmail_service()
    msg = (
        service.users()
        .messages()
        .get(userId="me", id=message_id, format="full")
        .execute()
    )
    return _message_to_dict(msg)


def fetch_emails_for_task(task: str, *, query: str | None = None, limit: int | None = None) -> list[dict]:
    """Fetch Gmail messages matching a natural-language summariser task."""
    query = query or _parse_query(task)
    limit = limit if limit is not None else _parse_limit(task)
    ids = _list_message_ids(query=query, limit=limit)
    return [_get_message(mid) for mid in ids]


def format_emails_for_llm(emails: list[dict]) -> str:
    if not emails:
        return "No matching emails found."
    blocks = []
    for i, email in enumerate(emails, start=1):
        blocks.append(
            f"Email {i}\n"
            f"From: {email['from']}\n"
            f"Subject: {email['subject']}\n"
            f"Date: {email['date']}\n"
            f"Preview: {email['snippet']}"
        )
    return "\n\n---\n\n".join(blocks)


def _build_mime(
    *,
    to: str,
    subject: str,
    body: str,
    in_reply_to: str = "",
    references: str = "",
) -> dict[str, str]:
    message = MIMEText(body)
    message["to"] = to
    message["subject"] = subject
    if in_reply_to:
        message["In-Reply-To"] = in_reply_to
        message["References"] = references or in_reply_to
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return {"raw": raw}


def send_email(*, to: str, subject: str, body: str) -> dict:
    service = _gmail_service()
    body_payload = _build_mime(to=to, subject=subject, body=body)
    return service.users().messages().send(userId="me", body=body_payload).execute()


def create_draft(*, to: str, subject: str, body: str) -> dict:
    service = _gmail_service()
    message = _build_mime(to=to, subject=subject, body=body)
    return service.users().drafts().create(userId="me", body={"message": message}).execute()


def reply_to_message(original: dict, body: str) -> dict:
    service = _gmail_service()
    to_addr = original.get("from_email") or original.get("from", "")
    subject = original.get("subject", "")
    if subject and not subject.lower().startswith("re:"):
        subject = f"Re: {subject}"
    message = _build_mime(
        to=to_addr,
        subject=subject,
        body=body,
        in_reply_to=original.get("message_id", ""),
        references=original.get("references") or original.get("message_id", ""),
    )
    message["threadId"] = original.get("thread_id")
    return service.users().messages().send(userId="me", body=message).execute()


def mark_as_read(message_ids: list[str]) -> None:
    service = _gmail_service()
    for mid in message_ids:
        service.users().messages().modify(
            userId="me", id=mid, body={"removeLabelIds": ["UNREAD"]},
        ).execute()


def archive_messages(message_ids: list[str]) -> None:
    service = _gmail_service()
    for mid in message_ids:
        service.users().messages().modify(
            userId="me", id=mid, body={"removeLabelIds": ["INBOX"]},
        ).execute()


def delete_messages(message_ids: list[str]) -> None:
    service = _gmail_service()
    for mid in message_ids:
        service.users().messages().trash(userId="me", id=mid).execute()


def _resolve_label_id(label_name: str) -> str:
    normalized = label_name.strip()
    system_labels = {
        "INBOX", "UNREAD", "STARRED", "IMPORTANT", "TRASH", "SPAM", "SENT", "DRAFT",
    }
    upper = normalized.upper().replace(" ", "_")
    if upper in system_labels:
        return upper
    service = _gmail_service()
    for label in service.users().labels().list(userId="me").execute().get("labels", []):
        if label["name"].lower() == normalized.lower():
            return label["id"]
    raise ValueError(f"Gmail label not found: {label_name}")


def add_label(message_ids: list[str], label_name: str) -> None:
    label_id = _resolve_label_id(label_name)
    service = _gmail_service()
    for mid in message_ids:
        service.users().messages().modify(
            userId="me", id=mid, body={"addLabelIds": [label_id]},
        ).execute()


def remove_label(message_ids: list[str], label_name: str) -> None:
    label_id = _resolve_label_id(label_name)
    service = _gmail_service()
    for mid in message_ids:
        service.users().messages().modify(
            userId="me", id=mid, body={"removeLabelIds": [label_id]},
        ).execute()


def _summarise_emails(task: str, intent: dict) -> str:
    emails = fetch_emails_for_task(
        task, query=intent.get("query"), limit=int(intent.get("limit", 5)),
    )
    email_text = format_emails_for_llm(emails)
    response = invoke_llm(
        groq_llm(max_tokens=768),
        [
            SystemMessage(content=SUMMARISE_PROMPT),
            HumanMessage(content=(
                f"User request: {task}\n"
                f"Emails fetched: {len(emails)} (summarise this many only)\n\n"
                f"{email_text}"
            )),
        ],
    )
    return _llm_text(response) or email_text


def _resolve_message_ids(intent: dict) -> list[str]:
    query = intent.get("query") or "in:inbox"
    limit = max(1, min(int(intent.get("limit", 1)), 20))
    ids = _list_message_ids(query=query, limit=limit)
    if not ids:
        raise ValueError(f"No emails matched query: {query}")
    return ids


def execute_gmail_task(task: str) -> str:
    """Parse intent and run the appropriate Gmail action."""
    intent = parse_gmail_intent(task)
    action = intent.get("action", "summarise")

    if action == "summarise":
        return _summarise_emails(task, intent)

    if action == "send":
        to = intent.get("to", "").strip()
        subject = intent.get("subject", "").strip()
        body = intent.get("body", "").strip()
        if not to or not body:
            raise ValueError("Send requests need a recipient and message body.")
        if not subject:
            subject = "(no subject)"
        result = send_email(to=to, subject=subject, body=body)
        return f"Email sent to {to} (message id: {result.get('id', 'unknown')})."

    if action == "draft":
        to = intent.get("to", "").strip()
        subject = intent.get("subject", "").strip() or "(no subject)"
        body = intent.get("body", "").strip()
        if not to or not body:
            raise ValueError("Draft requests need a recipient and message body.")
        draft = create_draft(to=to, subject=subject, body=body)
        return f"Draft saved for {to} (draft id: {draft.get('id', 'unknown')})."

    if action == "reply":
        ids = _resolve_message_ids({**intent, "limit": 1})
        original = _get_message(ids[0])
        body = intent.get("body", "").strip()
        if not body:
            raise ValueError("Reply requests need message body text.")
        result = reply_to_message(original, body)
        return (
            f"Reply sent to {original.get('from')} "
            f"regarding \"{original.get('subject')}\" "
            f"(message id: {result.get('id', 'unknown')})."
        )

    message_ids = _resolve_message_ids(intent)
    count = len(message_ids)

    if action == "mark_read":
        mark_as_read(message_ids)
        return f"Marked {count} email(s) as read."

    if action == "archive":
        archive_messages(message_ids)
        return f"Archived {count} email(s)."

    if action == "delete":
        delete_messages(message_ids)
        return f"Moved {count} email(s) to trash."

    if action == "add_label":
        label = intent.get("label", "").strip()
        if not label:
            raise ValueError("Label name required for add_label action.")
        add_label(message_ids, label)
        return f"Added label \"{label}\" to {count} email(s)."

    if action == "remove_label":
        label = intent.get("label", "").strip()
        if not label:
            raise ValueError("Label name required for remove_label action.")
        remove_label(message_ids, label)
        return f"Removed label \"{label}\" from {count} email(s)."

    raise ValueError(f"Unsupported Gmail action: {action}")
