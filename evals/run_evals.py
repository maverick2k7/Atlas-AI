"""Evaluation script: measures supervisor routing accuracy across 30 prompts.

Runs each prompt from test_prompts.json through the LangGraph graph,
checks if active_agent matches expected_agent, and saves results to
evals/results.csv.

Run from the backend/ directory:
    .\\venv\\Scripts\\python.exe ..\\evals\\run_evals.py
"""

import sys
import os

# Must be set BEFORE any sentence-transformers / HF imports to prevent
# the model from attempting network downloads and hanging.
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"

import json
import csv
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup — allow imports from backend/
# ---------------------------------------------------------------------------

SCRIPT_DIR  = Path(__file__).resolve().parent        # evals/
BACKEND_DIR = SCRIPT_DIR.parent / "backend"          # backend/
EVALS_DIR   = SCRIPT_DIR                             # evals/

sys.path.insert(0, str(BACKEND_DIR))

# ---------------------------------------------------------------------------
# Load graph (triggers LangSmith tracing env setup via api.main imports)
# ---------------------------------------------------------------------------

from graph.workflow import app_graph  # noqa: E402

# ---------------------------------------------------------------------------
# Load test prompts
# ---------------------------------------------------------------------------

PROMPTS_FILE = EVALS_DIR / "test_prompts.json"
RESULTS_FILE = EVALS_DIR / "results.csv"

with open(PROMPTS_FILE, "r", encoding="utf-8") as f:
    test_cases = json.load(f)

# ---------------------------------------------------------------------------
# Run evaluations
# ---------------------------------------------------------------------------

print("=" * 70)
print("Atlas — Supervisor Routing Accuracy Eval")
print(f"Running {len(test_cases)} prompts...")
print("=" * 70)

results = []
correct = 0
total   = len(test_cases)

for i, tc in enumerate(test_cases, 1):
    prompt         = tc["prompt"]
    expected_agent = tc["expected_agent"]

    print(f"\n[{i:02d}/{total}] {prompt[:65]}{'...' if len(prompt) > 65 else ''}")
    print(f"       Expected : {expected_agent}")

    initial_state = {
        "task":           prompt,
        "messages":       [{"role": "user", "content": prompt}],
        "results":        {},
        "active_agent":   "",
        "primary_agent":  "",
        "agent_plan":     [],
        "plan_index":     0,
        "memory_context": [],
        "session_id":     f"eval-{i:03d}",
    }

    start_time = time.time()
    routed_to  = "ERROR"
    status     = "FAIL"
    error_msg  = ""

    try:
        final_state = app_graph.invoke(initial_state)
        routed_to = final_state.get("primary_agent") or (
            final_state.get("agent_plan") or [final_state.get("active_agent", "unknown")]
        )[0]
        elapsed     = time.time() - start_time

        if routed_to == expected_agent:
            status  = "PASS"
            correct += 1
            print(f"       Got      : {routed_to}  PASS  ({elapsed:.1f}s)")
        else:
            print(f"       Got      : {routed_to}  FAIL  ({elapsed:.1f}s)")

    except Exception as exc:
        elapsed   = time.time() - start_time
        error_msg = str(exc)
        print(f"       ERROR    : {error_msg[:80]}")

    results.append({
        "prompt":          prompt,
        "expected_agent":  expected_agent,
        "routed_to":       routed_to,
        "status":          status,
        "elapsed_seconds": f"{elapsed:.2f}",
        "error":           error_msg,
    })

# ---------------------------------------------------------------------------
# Save results CSV
# ---------------------------------------------------------------------------

fieldnames = ["prompt", "expected_agent", "routed_to", "status",
              "elapsed_seconds", "error"]

with open(RESULTS_FILE, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(results)

# ---------------------------------------------------------------------------
# Print summary
# ---------------------------------------------------------------------------

accuracy = correct / total * 100

print("\n" + "=" * 70)
print("EVAL RESULTS")
print("=" * 70)
print(f"  Total prompts   : {total}")
print(f"  Correct routing : {correct}")
print(f"  Wrong routing   : {total - correct}")
print(f"  Accuracy        : {accuracy:.1f}%")
print(f"\n  Results saved to: {RESULTS_FILE}")

# Per-agent breakdown
agents = ["researcher", "writer", "scheduler", "summariser"]
print("\n  Per-agent accuracy:")
for agent in agents:
    agent_cases   = [r for r in results if r["expected_agent"] == agent]
    agent_correct = sum(1 for r in agent_cases if r["status"] == "PASS")
    agent_total   = len(agent_cases)
    agent_pct     = agent_correct / agent_total * 100 if agent_total else 0
    print(f"    {agent:<12} {agent_correct}/{agent_total}  ({agent_pct:.0f}%)")

print("=" * 70)

if accuracy >= 80:
    print(f"  [TARGET MET] {accuracy:.1f}% >= 80% (resume-ready!)")
else:
    print(f"  [BELOW TARGET] {accuracy:.1f}% < 80% (tune the supervisor prompt)")

print("=" * 70)
