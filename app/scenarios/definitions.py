"""
scenarios/definitions.py

All named Phase 2 scenarios plus the three original Phase 1 scenarios.

Each scenario is a ScenarioConfig instance.  The agent and main.py import
SCENARIOS (dict) and get_scenario() from here.

Scenario key → CLI argument:
  phase1          python -m app.main phase1
  success         python -m app.main success
  recovery        python -m app.main recovery
  repeated_failure  python -m app.main repeated_failure
  empty_result    python -m app.main empty_result
  impossible      python -m app.main impossible
  loop            python -m app.main loop
"""

from app.scenarios.config import ScenarioConfig, ToolFailureConfig

# ---------------------------------------------------------------------------
# Phase 1 (unchanged behaviour — no failure injection)
# ---------------------------------------------------------------------------

PHASE1_WEATHER = ScenarioConfig(
    name="phase1_weather",
    description="[Phase 1] Normal weather query — Hyderabad",
    task="What is the weather in Hyderabad?",
    phase="1",
)

PHASE1_FLIGHT = ScenarioConfig(
    name="phase1_flight",
    description="[Phase 1] Normal flight search — Hyderabad → Delhi",
    task="Find a flight from Hyderabad to Delhi.",
    phase="1",
)

PHASE1_SEARCH = ScenarioConfig(
    name="phase1_search",
    description="[Phase 1] Normal web search — Python programming",
    task="Search for information about Python programming.",
    phase="1",
)

# ---------------------------------------------------------------------------
# Scenario 1 — SUCCESS
# Identical to Phase 1 but labelled as a Phase 2 scenario.
# ---------------------------------------------------------------------------

SCENARIO_SUCCESS = ScenarioConfig(
    name="success",
    description="[Scenario 1] Normal success — weather query for Hyderabad",
    task="What is the weather in Hyderabad?",
    tool_configs=[],        # no failure injection; tool succeeds immediately
    max_iterations=5,
)

# ---------------------------------------------------------------------------
# Scenario 2 — TEMPORARY FAILURE → RECOVERY
# flight_search_tool fails on the first call, succeeds on the second.
# fail_times=1 means: fail exactly once, then succeed.
# ---------------------------------------------------------------------------

SCENARIO_RECOVERY = ScenarioConfig(
    name="recovery",
    description=(
        "[Scenario 2] Temporary failure → recovery — "
        "flight search fails once, then succeeds"
    ),
    task="Find a flight from Hyderabad to Delhi.",
    tool_configs=[
        ToolFailureConfig(
            tool_name="flight_search_tool",
            fail_times=1,
            failure_message=(
                "Flight search service is temporarily unavailable. "
                "Please try again."
            ),
        )
    ],
    max_iterations=5,
)

# ---------------------------------------------------------------------------
# Scenario 3 — REPEATED FAILURE
# flight_search_tool always fails.  Agent will retry until max_iterations.
# Intentionally bad — designed to be caught later by the abstention middleware.
# ---------------------------------------------------------------------------

SCENARIO_REPEATED_FAILURE = ScenarioConfig(
    name="repeated_failure",
    description=(
        "[Scenario 3] Repeated failure — "
        "flight search fails on every call (abstention bait)"
    ),
    task="Find a flight from Hyderabad to Delhi.",
    tool_configs=[
        ToolFailureConfig(
            tool_name="flight_search_tool",
            always_fail=True,
            failure_message=(
                "Flight search service is down. Unable to retrieve results."
            ),
        )
    ],
    max_iterations=5,
)

# ---------------------------------------------------------------------------
# Scenario 4 — EMPTY RESULT
# search_tool returns status=success but results=[].
# The LLM must decide what to do with an empty observation.
# ---------------------------------------------------------------------------

SCENARIO_EMPTY_RESULT = ScenarioConfig(
    name="empty_result",
    description=(
        "[Scenario 4] Empty result — "
        "search returns success with zero results"
    ),
    task="Search for information about xzqwerty_unknown_topic_42.",
    tool_configs=[
        ToolFailureConfig(
            tool_name="search_tool",
            empty_result=True,
            failure_message="No results found.",   # not used in empty mode, but kept for clarity
        )
    ],
    max_iterations=5,
)

# ---------------------------------------------------------------------------
# Scenario 5 — IMPOSSIBLE / UNSUPPORTED TASK
# User asks for a flight to Mars — always fails with a clear unsupported error.
# ---------------------------------------------------------------------------

SCENARIO_IMPOSSIBLE = ScenarioConfig(
    name="impossible",
    description=(
        "[Scenario 5] Impossible task — "
        "flight to Mars always fails"
    ),
    task="Book a flight from Hyderabad to Mars.",
    tool_configs=[
        ToolFailureConfig(
            tool_name="flight_search_tool",
            always_fail=True,
            failure_message=(
                "No flights available for the requested route. "
                "Destination 'Mars' is not a supported location."
            ),
        )
    ],
    max_iterations=5,
)

# ---------------------------------------------------------------------------
# Scenario 6 — REPEATED TOOL CALL / LOOP
# search_tool returns empty results every time.
# We want to observe whether the LLM loops, replans, or gives up.
# max_iterations=6 to make the looping behaviour more visible.
# ---------------------------------------------------------------------------

SCENARIO_LOOP = ScenarioConfig(
    name="loop",
    description=(
        "[Scenario 6] Loop — "
        "search always returns empty results; observe LLM loop behaviour"
    ),
    task="Search for information about xzqwerty_unknown_topic_42.",
    tool_configs=[
        ToolFailureConfig(
            tool_name="search_tool",
            empty_result=True,
        )
    ],
    max_iterations=6,   # higher cap to expose looping
)

# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

SCENARIOS: dict[str, ScenarioConfig] = {
    # Phase 1 (accessible via CLI for regression checks)
    "phase1":            PHASE1_WEATHER,        # runs all three P1 tasks when chosen
    # Phase 2
    "success":           SCENARIO_SUCCESS,
    "recovery":          SCENARIO_RECOVERY,
    "repeated_failure":  SCENARIO_REPEATED_FAILURE,
    "empty_result":      SCENARIO_EMPTY_RESULT,
    "impossible":        SCENARIO_IMPOSSIBLE,
    "loop":              SCENARIO_LOOP,
}


def get_scenario(name: str) -> ScenarioConfig:
    """
    Look up a scenario by its CLI key.

    Raises:
        KeyError: with a helpful message listing valid names.
    """
    if name not in SCENARIOS:
        valid = ", ".join(sorted(SCENARIOS.keys()))
        raise KeyError(
            f"Unknown scenario '{name}'. Valid options: {valid}"
        )
    return SCENARIOS[name]
