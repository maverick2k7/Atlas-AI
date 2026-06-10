"""Direct Google Calendar API access — avoids MCP token limits and setup issues."""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone

from googleapiclient.discovery import build
from langchain_core.messages import HumanMessage, SystemMessage

from llm import groq_llm, invoke_llm
from mcp_servers.client import get_oauth_credentials

_PARSE_PROMPT = """\
You parse calendar requests into JSON. Reply with ONLY a JSON object, no markdown.

Fields:
- action: "create" or "list"
- title: event title (for create)
- start: ISO 8601 local datetime without timezone suffix, e.g. "2026-06-10T15:00:00"
- end: ISO 8601 local datetime (for create)
- limit: integer (for list, default 5)

Rules:
- Infer title from the user's words (e.g. "study session").
- Resolve relative dates like "tomorrow" using today's date below.
- If duration is given (e.g. "2 hours"), compute end from start.
- Default duration is 1 hour when not specified.

Today: {today} ({weekday})"""


def _calendar_service():
    creds = get_oauth_credentials()
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def _primary_timezone() -> str:
    service = _calendar_service()
    cal = service.calendars().get(calendarId="primary").execute()
    return cal.get("timeZone", "UTC")


def _extract_json(text: str) -> dict:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise ValueError(f"Could not parse calendar intent: {text[:200]}")


def parse_calendar_task(task: str) -> dict:
    """Use the LLM to turn a natural-language request into structured calendar data."""
    now = datetime.now()
    response = invoke_llm(
        groq_llm(max_tokens=256),
        [
            SystemMessage(content=_PARSE_PROMPT.format(
                today=now.strftime("%Y-%m-%d"),
                weekday=now.strftime("%A"),
            )),
            HumanMessage(content=task),
        ],
    )
    raw = response.content
    if isinstance(raw, list):
        raw = " ".join(
            part.get("text", "") if isinstance(part, dict) else str(part)
            for part in raw
        )
    return _extract_json(str(raw))


def create_calendar_event(*, title: str, start: str, end: str, tz: str | None = None) -> dict:
    """Create an event on the user's primary calendar."""
    tz = tz or _primary_timezone()
    service = _calendar_service()
    body = {
        "summary": title,
        "start": {"dateTime": start, "timeZone": tz},
        "end": {"dateTime": end, "timeZone": tz},
    }
    return service.events().insert(calendarId="primary", body=body).execute()


def list_upcoming_events(*, limit: int = 5) -> list[dict]:
    """Return upcoming events from the primary calendar."""
    service = _calendar_service()
    now = datetime.now(timezone.utc).isoformat()
    result = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=now,
            maxResults=limit,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    events = []
    for item in result.get("items", []):
        start = item.get("start", {})
        events.append({
            "title": item.get("summary", "(no title)"),
            "start": start.get("dateTime") or start.get("date", ""),
            "end": (item.get("end", {}).get("dateTime")
                    or item.get("end", {}).get("date", "")),
        })
    return events


def _format_event_time(start: str, end: str, tz: str) -> str:
    try:
        start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
        return (
            f"{start_dt.strftime('%A %d %B %Y, %I:%M %p')} – "
            f"{end_dt.strftime('%I:%M %p')} ({tz})"
        )
    except ValueError:
        return f"{start} – {end}"


def execute_calendar_task(task: str) -> str:
    """Parse a natural-language calendar request and execute it via the Calendar API."""
    parsed = parse_calendar_task(task)
    action = parsed.get("action", "create")
    tz = _primary_timezone()

    if action == "list":
        limit = int(parsed.get("limit", 5))
        events = list_upcoming_events(limit=limit)
        if not events:
            return "No upcoming events found on your calendar."
        lines = ["Upcoming events:"]
        for i, ev in enumerate(events, start=1):
            lines.append(f"{i}. {ev['title']} — {ev['start']}")
        return "\n".join(lines)

    title = parsed.get("title") or "Event"
    start = parsed.get("start")
    end = parsed.get("end")
    if not start or not end:
        raise ValueError("Could not determine event start/end time from your request.")

    event = create_calendar_event(title=title, start=start, end=end, tz=tz)
    when = _format_event_time(start, end, tz)
    link = event.get("htmlLink", "")
    msg = f'Created "{title}" for {when}.'
    if link:
        msg += f"\nView in Google Calendar: {link}"
    return msg
