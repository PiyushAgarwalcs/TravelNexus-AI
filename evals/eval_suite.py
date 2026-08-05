#!/usr/bin/env python
"""
TravelNexus-AI — Evaluation Suite
===================================
Measures guardrail accuracy and supervisor routing accuracy
against curated test cases using the REAL LLM.

Usage (from project root):
    python evals/eval_suite.py

Requires:
    - Valid API keys in .env (GROQ_API_KEY, DATABASE_URL, etc.)
    - All production dependencies installed
"""

import json
import sys
import time
from pathlib import Path

# Ensure project root is on the path so we can import backend
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend import supervisor_agent  # noqa: E402


# ═══════════════════════════════════════════════════════
# Load test cases
# ═══════════════════════════════════════════════════════


def load_test_cases() -> list[dict]:
    cases_path = Path(__file__).parent / "test_cases.json"
    with open(cases_path, encoding="utf-8") as f:
        return json.load(f)


# ═══════════════════════════════════════════════════════
# Guardrail evaluation
# ═══════════════════════════════════════════════════════


def run_guardrail_eval(cases: list[dict]) -> list[dict]:
    results = []

    for case in cases:
        query = case["query"]
        expected = case["expected_allowed"]
        state = {"user_query": query, "llm_calls": 0}

        start = time.time()
        try:
            output = supervisor_agent(state)
            actual = output.get("guardrail_allowed", True)
            latency = time.time() - start
            results.append(
                {
                    "query": query[:60],
                    "expected": expected,
                    "actual": actual,
                    "correct": actual == expected,
                    "latency_s": round(latency, 2),
                }
            )
        except Exception as exc:
            results.append(
                {
                    "query": query[:60],
                    "expected": expected,
                    "actual": "ERROR",
                    "correct": False,
                    "latency_s": round(time.time() - start, 2),
                    "error": str(exc),
                }
            )

    return results


# ═══════════════════════════════════════════════════════
# Routing evaluation
# ═══════════════════════════════════════════════════════


def run_routing_eval(cases: list[dict]) -> list[dict]:
    routing_cases = [
        c for c in cases if c["expected_allowed"] and "expected_agents" in c
    ]
    results = []

    for case in routing_cases:
        query = case["query"]
        expected = set(case["expected_agents"])
        state = {"user_query": query, "llm_calls": 0}

        try:
            output = supervisor_agent(state)
            actual = set(output.get("selected_agents", []))
            results.append(
                {
                    "query": query[:55],
                    "expected": sorted(expected),
                    "actual": sorted(actual),
                    "exact_match": actual == expected,
                    "subset_match": expected.issubset(actual),
                }
            )
        except Exception as exc:
            results.append(
                {
                    "query": query[:55],
                    "expected": sorted(expected),
                    "actual": ["ERROR"],
                    "exact_match": False,
                    "subset_match": False,
                    "error": str(exc),
                }
            )

    return results


# ═══════════════════════════════════════════════════════
# Report printer
# ═══════════════════════════════════════════════════════


def print_report(
    guardrail_results: list[dict],
    routing_results: list[dict],
) -> None:
    W = 66

    print()
    print("=" * W)
    print("  TravelNexus-AI  —  Evaluation Report")
    print("=" * W)

    # ── Guardrail summary ──
    total = len(guardrail_results)
    correct = sum(r["correct"] for r in guardrail_results)

    should_allow = [r for r in guardrail_results if r["expected"]]
    should_block = [r for r in guardrail_results if not r["expected"]]

    false_pos = sum(1 for r in should_block if r["actual"] is True)
    false_neg = sum(1 for r in should_allow if r["actual"] is False)

    avg_lat = (
        sum(r["latency_s"] for r in guardrail_results) / total if total else 0
    )

    print(f"\n  GUARDRAIL ACCURACY:       {correct}/{total}  "
          f"({correct / max(total, 1) * 100:.1f}%)")
    print(f"  False Positives (leaked): {false_pos}/{len(should_block)}")
    print(f"  False Negatives (blocked):{false_neg}/{len(should_allow)}")
    print(f"  Avg Latency:              {avg_lat:.2f}s")

    # Detail table
    print(f"\n  {'Query':<50} {'Exp':>5} {'Act':>5} {'':>3}")
    print("  " + "-" * (W - 4))

    for r in guardrail_results:
        mark = "[OK]" if r["correct"] else "[FAIL]"
        exp = "allow" if r["expected"] else "block"
        if r["actual"] is True:
            act = "allow"
        elif r["actual"] is False:
            act = "block"
        else:
            act = "ERR"
        print(f"  {r['query']:<50} {exp:>5} {act:>5} {mark:>3}")

    # ── Routing summary ──
    if routing_results:
        r_total = len(routing_results)
        exact = sum(r["exact_match"] for r in routing_results)
        subset = sum(r["subset_match"] for r in routing_results)

        print(f"\n  ROUTING EXACT MATCH:      {exact}/{r_total}  "
              f"({exact / max(r_total, 1) * 100:.1f}%)")
        print(f"  ROUTING SUBSET MATCH:     {subset}/{r_total}  "
              f"({subset / max(r_total, 1) * 100:.1f}%)")

        print(f"\n  {'Query':<45} {'Match':>6}")
        print("  " + "-" * 55)

        for r in routing_results:
            if r["exact_match"]:
                mark = " [OK]"
            elif r["subset_match"]:
                mark = " [WARN]"
            else:
                mark = " [FAIL]"
            print(f"  {r['query']:<45} {mark}")
            if not r["exact_match"]:
                print(f"    expected: {r['expected']}")
                print(f"    actual:   {r['actual']}")

    print()
    print("=" * W)
    print()


# ═══════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════


def main() -> None:
    cases = load_test_cases()
    print(f"\nLoaded {len(cases)} test cases.")

    print("Running guardrail evaluation …")
    guardrail = run_guardrail_eval(cases)

    print("Running routing evaluation …")
    routing = run_routing_eval(cases)

    print_report(guardrail, routing)


if __name__ == "__main__":
    main()
