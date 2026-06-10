"""Routing-only eval: tests agent planning without running full agents.

Uses deterministic plan_agents() rules — fast, no API keys required.
Run from the backend/ directory:
    .\\venv\\Scripts\\python.exe ..\\evals\\run_routing_eval.py
"""

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent / "backend"
EVALS_DIR = SCRIPT_DIR

sys.path.insert(0, str(BACKEND_DIR))

import json
import csv
import time

from agents.routing import plan_agents

PROMPTS_FILE = EVALS_DIR / "test_prompts.json"
MULTI_FILE = EVALS_DIR / "test_multi_prompts.json"
RESULTS_FILE = EVALS_DIR / "results.csv"
MULTI_RESULTS_FILE = EVALS_DIR / "multi_results.csv"


def run_single_agent_eval() -> tuple[list[dict], int, int]:
    with open(PROMPTS_FILE, encoding="utf-8") as f:
        test_cases = json.load(f)

    print("=" * 70)
    print("Atlas — Single-Agent Routing Eval (deterministic plan_agents)")
    print(f"Running {len(test_cases)} prompts...")
    print("=" * 70)

    results = []
    correct = 0

    for i, tc in enumerate(test_cases, 1):
        prompt = tc["prompt"]
        expected = tc["expected_agent"]
        plan = plan_agents(prompt)
        routed = plan[0] if plan else "unknown"
        status = "PASS" if routed == expected else "FAIL"
        if status == "PASS":
            correct += 1

        label = prompt[:65] + ("..." if len(prompt) > 65 else "")
        print(f"\n[{i:02d}/{len(test_cases)}] {label}")
        print(f"       Expected : {expected}")
        print(f"       Got      : {routed}  {status}")

        results.append({
            "prompt": prompt,
            "expected_agent": expected,
            "routed_to": routed,
            "agent_plan": " -> ".join(plan),
            "status": status,
            "elapsed_seconds": "0.00",
            "error": "",
        })

    return results, correct, len(test_cases)


def run_multi_agent_eval() -> tuple[list[dict], int, int]:
    if not MULTI_FILE.exists():
        return [], 0, 0

    with open(MULTI_FILE, encoding="utf-8") as f:
        test_cases = json.load(f)

    print("\n" + "=" * 70)
    print("Atlas — Multi-Agent Pipeline Eval")
    print(f"Running {len(test_cases)} prompts...")
    print("=" * 70)

    results = []
    correct = 0

    for i, tc in enumerate(test_cases, 1):
        prompt = tc["prompt"]
        expected_plan = tc["expected_plan"]
        plan = plan_agents(prompt)
        status = "PASS" if plan == expected_plan else "FAIL"
        if status == "PASS":
            correct += 1

        print(f"\n[{i:02d}/{len(test_cases)}] {prompt[:70]}...")
        print(f"       Expected : {' -> '.join(expected_plan)}")
        print(f"       Got      : {' -> '.join(plan) if plan else '(empty)'}  {status}")

        results.append({
            "prompt": prompt,
            "expected_plan": " -> ".join(expected_plan),
            "actual_plan": " -> ".join(plan),
            "status": status,
        })

    return results, correct, len(test_cases)


def _save_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _print_breakdown(results: list[dict], agent_key: str = "expected_agent") -> None:
    agents = ["researcher", "writer", "scheduler", "summariser"]
    print("\n  Per-agent accuracy:")
    for agent in agents:
        cases = [r for r in results if r.get(agent_key) == agent]
        ok = sum(1 for r in cases if r["status"] == "PASS")
        total = len(cases)
        pct = ok / total * 100 if total else 0
        print(f"    {agent:<12} {ok}/{total}  ({pct:.0f}%)")


if __name__ == "__main__":
    start = time.time()
    single_results, single_ok, single_total = run_single_agent_eval()
    multi_results, multi_ok, multi_total = run_multi_agent_eval()
    elapsed = time.time() - start

    _save_csv(
        RESULTS_FILE,
        single_results,
        ["prompt", "expected_agent", "routed_to", "agent_plan", "status", "elapsed_seconds", "error"],
    )

    accuracy = single_ok / single_total * 100 if single_total else 0

    print("\n" + "=" * 70)
    print("SINGLE-AGENT ROUTING RESULTS")
    print("=" * 70)
    print(f"  Correct : {single_ok}/{single_total}")
    print(f"  Accuracy: {accuracy:.1f}%")
    print(f"  Saved to: {RESULTS_FILE}")
    _print_breakdown(single_results)

    if multi_total:
        multi_acc = multi_ok / multi_total * 100
        _save_csv(
            MULTI_RESULTS_FILE,
            multi_results,
            ["prompt", "expected_plan", "actual_plan", "status"],
        )
        print("\n" + "=" * 70)
        print("MULTI-AGENT PIPELINE RESULTS")
        print("=" * 70)
        print(f"  Correct : {multi_ok}/{multi_total}")
        print(f"  Accuracy: {multi_acc:.1f}%")
        print(f"  Saved to: {MULTI_RESULTS_FILE}")

    print(f"\n  Total eval time: {elapsed:.1f}s")
    print("=" * 70)
    if accuracy >= 80:
        print(f"  [TARGET MET] {accuracy:.1f}% >= 80%")
    else:
        print(f"  [BELOW TARGET] {accuracy:.1f}% < 80%")
    print("=" * 70)
