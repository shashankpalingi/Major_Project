"""
main.py — Entry point for the Agentic Abstention project (Phase 1 + Phase 2).

Usage
-----
Phase 1 (all three original tests):
    python -m app.main
    python -m app.main phase1

Phase 2 scenarios (one at a time):
    python -m app.main success
    python -m app.main recovery
    python -m app.main repeated_failure
    python -m app.main empty_result
    python -m app.main impossible
    python -m app.main loop

Run all Phase 2 scenarios in sequence:
    python -m app.main all

List available scenarios:
    python -m app.main list
"""

from __future__ import annotations

import os
import sys
from dotenv import load_dotenv

# Load .env before any module that reads GROQ_API_KEY.
load_dotenv()

from app.agent.agent import Agent                          # noqa: E402
from app.scenarios.definitions import (                   # noqa: E402
    SCENARIOS,
    get_scenario,
    PHASE1_WEATHER,
    PHASE1_FLIGHT,
    PHASE1_SEARCH,
)
from app.scenarios.config import ScenarioConfig            # noqa: E402

WIDE  = "=" * 70
THIN  = "-" * 70


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _check_api_key() -> None:
    key = os.getenv("GROQ_API_KEY", "")
    if not key or key == "your_groq_api_key_here":
        print(
            "\n❌  GROQ_API_KEY is not configured.\n"
            "    Edit .env and replace 'your_groq_api_key_here' with your\n"
            "    real key from https://console.groq.com\n"
        )
        sys.exit(1)


def _banner(title: str, subtitle: str = "") -> None:
    print(f"\n{WIDE}")
    print(f"  {title}")
    if subtitle:
        print(f"  {subtitle}")
    print(WIDE)


def _run_scenario(agent: Agent, scenario: ScenarioConfig) -> None:
    """Run a single scenario, print its final answer, and catch any errors."""
    _banner(
        f"SCENARIO: {scenario.name.upper()}",
        scenario.description,
    )
    print(f"  Task: {scenario.task}\n")

    try:
        answer = agent.run(scenario.task, scenario=scenario)
        print(f"\n{'─'*70}")
        print("✅  FINAL ANSWER:")
        print(answer)
        print(f"{'─'*70}\n")
    except Exception as exc:          # noqa: BLE001
        print(f"\n❌  ERROR: {exc}\n")


def _list_scenarios() -> None:
    _banner("Available Scenarios")
    rows = [
        ("phase1",           "Run all three original Phase 1 tests"),
        ("success",          "[P2-1] Normal success — weather query"),
        ("recovery",         "[P2-2] Temporary failure → recovery (flight)"),
        ("repeated_failure", "[P2-3] Repeated failure — always fails (flight)"),
        ("empty_result",     "[P2-4] Empty result — search returns []"),
        ("impossible",       "[P2-5] Impossible task — flight to Mars"),
        ("loop",             "[P2-6] Loop — search always empty, observe LLM"),
        ("all",              "Run all six Phase 2 scenarios in sequence"),
    ]
    for key, desc in rows:
        print(f"  {key:<22}  {desc}")
    print()


# ---------------------------------------------------------------------------
# Phase 1 runner (three tasks, no scenario config)
# ---------------------------------------------------------------------------

PHASE1_TASKS = [
    {"id": 1, "description": "Weather query",     "config": PHASE1_WEATHER},
    {"id": 2, "description": "Flight search",     "config": PHASE1_FLIGHT},
    {"id": 3, "description": "General web search","config": PHASE1_SEARCH},
]


def run_phase1(agent: Agent) -> None:
    _banner(
        "Agentic Abstention — Phase 1",
        "Multi-step LLM Agent with Mock Tools",
    )
    for t in PHASE1_TASKS:
        _banner(
            f"TEST {t['id']}: {t['description']}",
            f"Task: {t['config'].task}",
        )
        try:
            # Phase 1 runs with no scenario config — pure normal behaviour.
            answer = agent.run(t["config"].task, scenario=None)
            print(f"\n✅  FINAL ANSWER:\n{answer}\n")
        except Exception as exc:   # noqa: BLE001
            print(f"\n❌  ERROR: {exc}\n")

    _banner("Phase 1 complete — all tests finished.")


# ---------------------------------------------------------------------------
# Phase 2 scenario order for "all"
# ---------------------------------------------------------------------------

PHASE2_ORDER = [
    "success",
    "recovery",
    "repeated_failure",
    "empty_result",
    "impossible",
    "loop",
]


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------

def main() -> None:
    _check_api_key()

    # Default: no argument → run Phase 1
    arg = sys.argv[1].lower().strip() if len(sys.argv) > 1 else "phase1"

    if arg == "list":
        _list_scenarios()
        return

    # Create a single agent reused for all scenarios in this process.
    agent = Agent()

    if arg in ("phase1", ""):
        run_phase1(agent)
        return

    if arg == "all":
        _banner(
            "Agentic Abstention — Phase 2",
            "Running all six Phase 2 scenarios",
        )
        for key in PHASE2_ORDER:
            scenario = get_scenario(key)
            _run_scenario(agent, scenario)
        _banner("Phase 2 complete — all scenarios finished.")
        return

    # Single named scenario
    try:
        scenario = get_scenario(arg)
    except KeyError as exc:
        print(f"\n❌  {exc}")
        print("    Run  python -m app.main list  to see available options.\n")
        sys.exit(1)

    _run_scenario(agent, scenario)


if __name__ == "__main__":
    main()
