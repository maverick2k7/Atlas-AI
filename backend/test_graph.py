"""Quick smoke-test for the LangGraph routing pipeline.

Tests single-agent routing (4 cases) and multi-agent chaining (1 case),
and prints whether the supervisor routed to the correct agent(s).

Run from inside backend/:
    .\venv\Scripts\python.exe test_graph.py
"""

import os
import sys

# Force SentenceTransformer offline (model already cached)
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"

from graph.workflow import app_graph  # noqa: E402

TEST_CASES = [
    {
        "prompt": "What are the latest developments in AI agents this week?",
        "expected": "researcher",
    },
    {
        "prompt": "Write a professional email declining a job offer.",
        "expected": "writer",
    },
    {
        "prompt": "Schedule a team meeting for next Monday at 10am.",
        "expected": "scheduler",
    },
    {
        "prompt": "Summarise my unread emails from today.",
        "expected": "summariser",
    },
    {
        "prompt": "Research the latest AI news and then draft me a short summary email.",
        "expected": "writer",   # last agent in chain: researcher → writer
    },
]

print("=" * 60)
print("Atlas — Graph Routing Smoke Test (Groq / llama-3.3-70b)")
print("=" * 60)

passed = 0
for i, tc in enumerate(TEST_CASES, 1):
    prompt = tc["prompt"]
    expected = tc["expected"]

    state = {
        "task": prompt,
        "messages": [{"role": "user", "content": prompt}],
        "results": {},
        "active_agent": "",
        "primary_agent": "",
        "agent_plan": [],
        "plan_index": 0,
        "memory_context": [],
        "session_id": f"test-{i:02d}",
    }

    print(f"\n[{i}/{len(TEST_CASES)}] {prompt}")
    print(f"      Expected : {expected}")

    try:
        final = app_graph.invoke(state)
        got = final.get("active_agent", "unknown")
        ok = "PASS" if got == expected else "FAIL"
        if got == expected:
            passed += 1
        print(f"      Got      : {got}  {ok}")
    except Exception as exc:
        print(f"      ERROR    : {exc}")

print("\n" + "=" * 60)
print(f"Result: {passed}/{len(TEST_CASES)} passed")
print("=" * 60)
