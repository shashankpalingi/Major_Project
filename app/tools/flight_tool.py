"""
flight_tool.py — Mock flight search tool (Phase 1 + Phase 2).

Phase 1 behaviour is unchanged when called without a scenario config:
  - known routes → success with flight list
  - unknown routes → no_flights_found

Phase 2 adds controlled failure injection via an optional
ToolFailureConfig passed in by the agent.  The config is never
part of the LLM-visible tool schema — it is injected internally.

Failure modes (driven by ToolFailureConfig):
  always_fail=True     → every call returns status "failure"
  fail_times=N         → first N calls fail, call N+1 succeeds
  (neither)            → normal success path (Phase 1 behaviour)
"""

from __future__ import annotations

from app.scenarios.config import ToolFailureConfig

# ---------------------------------------------------------------------------
# Deterministic mock data
# ---------------------------------------------------------------------------
MOCK_FLIGHTS: dict[tuple[str, str], list[dict]] = {
    ("hyderabad", "delhi"): [
        {
            "flight_number": "AI-501",
            "airline": "Air India",
            "departure": "06:00",
            "arrival": "08:15",
            "duration": "2h 15m",
            "price_inr": 4500,
            "seats_available": 12,
        },
        {
            "flight_number": "6E-203",
            "airline": "IndiGo",
            "departure": "10:30",
            "arrival": "12:45",
            "duration": "2h 15m",
            "price_inr": 3800,
            "seats_available": 0,   # sold out — demonstrates unsuccessful result
        },
        {
            "flight_number": "UK-812",
            "airline": "Vistara",
            "departure": "18:00",
            "arrival": "20:20",
            "duration": "2h 20m",
            "price_inr": 5200,
            "seats_available": 5,
        },
    ],
    ("delhi", "hyderabad"): [
        {
            "flight_number": "AI-502",
            "airline": "Air India",
            "departure": "09:00",
            "arrival": "11:15",
            "duration": "2h 15m",
            "price_inr": 4600,
            "seats_available": 8,
        },
        {
            "flight_number": "6E-204",
            "airline": "IndiGo",
            "departure": "14:00",
            "arrival": "16:15",
            "duration": "2h 15m",
            "price_inr": 3900,
            "seats_available": 20,
        },
    ],
    ("mumbai", "delhi"): [
        {
            "flight_number": "6E-101",
            "airline": "IndiGo",
            "departure": "07:00",
            "arrival": "09:10",
            "duration": "2h 10m",
            "price_inr": 4200,
            "seats_available": 15,
        },
    ],
    ("bangalore", "mumbai"): [
        {
            "flight_number": "SG-301",
            "airline": "SpiceJet",
            "departure": "11:00",
            "arrival": "13:05",
            "duration": "2h 05m",
            "price_inr": 3500,
            "seats_available": 3,
        },
    ],
}

# Per-tool call counter — keyed by (source, destination) so each unique
# route has its own independent failure counter.
_call_counters: dict[tuple[str, str], int] = {}


def reset_call_counter() -> None:
    """Reset all call counters. Call this between scenario runs."""
    _call_counters.clear()


# ---------------------------------------------------------------------------
# Public tool function
# ---------------------------------------------------------------------------

def flight_search_tool(
    source: str,
    destination: str,
    _scenario: ToolFailureConfig | None = None,
) -> dict:
    """
    Search for mock flights between source and destination.

    Args:
        source:      Departure city name (case-insensitive).
        destination: Arrival city name (case-insensitive).
        _scenario:   Optional ToolFailureConfig injected by the agent.
                     NOT exposed in the LLM tool schema.

    Returns:
        A dict with:
          - status: "success" | "no_flights_found" | "failure"
          - source / destination
          - flights: list of flight dicts (on success)
          - message / error: human-readable description
    """
    route_key = (source.strip().lower(), destination.strip().lower())

    # ── Phase 2: failure injection ────────────────────────────────────
    if _scenario is not None:

        # always_fail: every call returns a failure (repeated_failure, impossible)
        if _scenario.always_fail:
            return {
                "status": "failure",
                "source": source,
                "destination": destination,
                "error": _scenario.failure_message,
            }

        # fail_times: fail the first N calls, then succeed
        if _scenario.fail_times > 0:
            call_count = _call_counters.get(route_key, 0) + 1
            _call_counters[route_key] = call_count

            if call_count <= _scenario.fail_times:
                return {
                    "status": "failure",
                    "source": source,
                    "destination": destination,
                    "error": _scenario.failure_message,
                    "attempt": call_count,
                    "hint": (
                        f"This is a temporary error (attempt {call_count} of "
                        f"{_scenario.fail_times} failures). Retrying may help."
                    ),
                }
            # Fall through to normal success path after N failures.

    # ── Phase 1 / normal path ─────────────────────────────────────────
    flights = MOCK_FLIGHTS.get(route_key, [])

    if not flights:
        return {
            "status": "no_flights_found",
            "source": source,
            "destination": destination,
            "flights": [],
            "message": (
                f"No flights found from {source} to {destination}. "
                "Try a different route or travel date."
            ),
        }

    available = [f for f in flights if f["seats_available"] > 0]
    sold_out  = [f for f in flights if f["seats_available"] == 0]

    summary_parts = [
        f"Found {len(flights)} flight(s) from {source} to {destination}.",
        f"{len(available)} available, {len(sold_out)} sold out.",
    ]
    if available:
        cheapest = min(available, key=lambda f: f["price_inr"])
        summary_parts.append(
            f"Cheapest available: {cheapest['airline']} {cheapest['flight_number']} "
            f"at ₹{cheapest['price_inr']}."
        )

    return {
        "status": "success",
        "source": source,
        "destination": destination,
        "flights": flights,
        "message": " ".join(summary_parts),
    }
