"""
agent.py — Core LLM Agent (Phase 1 + Phase 2).

Implements the ReAct-style agent loop:
  User Task → LLM → Tool Decision → Tool Execution → Observation → LLM → Final Answer

Phase 2 additions:
  - Accepts an optional ScenarioConfig that controls tool failure injection.
  - Injects the matching ToolFailureConfig as `_scenario` into each tool call
    BEFORE dispatching, keeping the injected kwarg invisible to the LLM schema.
  - Structured per-iteration logging that clearly shows every step.

Loop invariant:
  1. Send conversation history to the LLM.
  2. If the LLM returns tool_calls  → execute each → append observations → loop.
  3. If the LLM returns plain text   → that is the final answer.
  4. After max_iterations            → return a capped-iterations message.
"""

from __future__ import annotations

import json
import logging
import os

from groq import Groq, APIError, APIConnectionError, RateLimitError

from app.tools.flight_tool import flight_search_tool, reset_call_counter
from app.tools.weather_tool import weather_tool
from app.tools.search_tool import search_tool
from app.scenarios.config import ScenarioConfig, ToolFailureConfig

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

THICK = "=" * 58
THIN  = "─" * 58


def _log_section(title: str) -> None:
    logger.info(THICK)
    logger.info("  %s", title)
    logger.info(THICK)


def _log_divider() -> None:
    logger.info(THIN)


# ---------------------------------------------------------------------------
# Tool registry
# Maps tool name → callable.  Add new tools here.
# ---------------------------------------------------------------------------
TOOL_REGISTRY: dict[str, callable] = {
    "flight_search_tool": flight_search_tool,
    "weather_tool":       weather_tool,
    "search_tool":        search_tool,
}

# ---------------------------------------------------------------------------
# Tool schemas (LLM-visible)
# _scenario is intentionally absent from every schema.
# ---------------------------------------------------------------------------
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "flight_search_tool",
            "description": (
                "Search for available flights between two cities. "
                "Returns flight options with prices, timings, and seat availability."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "source": {
                        "type": "string",
                        "description": "The departure city name (e.g. 'Hyderabad').",
                    },
                    "destination": {
                        "type": "string",
                        "description": "The arrival city name (e.g. 'Delhi').",
                    },
                },
                "required": ["source", "destination"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "weather_tool",
            "description": (
                "Get the current weather conditions for a city. "
                "Returns temperature, humidity, wind speed, and a short forecast."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "The city name (e.g. 'Hyderabad').",
                    },
                },
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_tool",
            "description": (
                "Search the web for information on a topic. "
                "Returns a list of relevant results with titles, URLs, and snippets."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query string.",
                    },
                },
                "required": ["query"],
            },
        },
    },
]

SYSTEM_PROMPT = """You are a helpful AI assistant with access to the following tools:
- flight_search_tool: search for flights between cities
- weather_tool: get current weather for a city
- search_tool: search the web for information

When answering a user's question:
1. If a tool is needed, call it with the correct arguments.
2. Once you receive the tool result, use it to form a clear, helpful final answer.
3. Do not make up information — use the tool results as your source of truth.
4. If the tool returns no results or an error, inform the user clearly.
5. If a tool fails, you may retry once. If it fails again, tell the user what happened.
"""


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class Agent:
    """
    ReAct-style LLM agent with optional Phase 2 scenario injection.

    When a ScenarioConfig is supplied to run(), the agent:
      - uses the scenario's max_iterations override
      - injects the matching ToolFailureConfig as `_scenario` into every
        tool call (invisible to the LLM)
      - resets per-tool call counters before the run so scenarios are
        reproducible across multiple calls in the same process
    """

    def __init__(
        self,
        model: str = "openai/gpt-oss-120b",
        max_iterations: int = 5,
    ) -> None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "GROQ_API_KEY is not set. Add it to your .env file."
            )
        self.model          = os.getenv("GROQ_MODEL", model)
        self.client         = Groq(api_key=api_key)
        self.max_iterations = max_iterations

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def run(
        self,
        user_task: str,
        scenario: ScenarioConfig | None = None,
    ) -> str:
        """
        Run the agent on a user task and return the final answer.

        Args:
            user_task: Natural-language task from the user.
            scenario:  Optional ScenarioConfig for Phase 2 failure injection.

        Returns:
            The LLM's final answer as a string.
        """
        # Per-scenario max_iterations override
        max_iter = scenario.max_iterations if scenario else self.max_iterations

        # Reset failure counters so each run is independent
        reset_call_counter()

        # ── Opening banner ────────────────────────────────────────────
        _log_section("USER TASK")
        logger.info("  %s", user_task)
        if scenario:
            logger.info("  Scenario : %s", scenario.name)
            logger.info("  Max iters: %d", max_iter)
        _log_divider()

        messages = [
            {"role": "system",  "content": SYSTEM_PROMPT},
            {"role": "user",    "content": user_task},
        ]

        for iteration in range(1, max_iter + 1):
            _log_section(f"ITERATION {iteration} / {max_iter}")

            # ── LLM call ──────────────────────────────────────────────
            response = self._call_llm(messages)
            if response is None:
                return "Sorry, I encountered an error communicating with the LLM."

            assistant_message = response.choices[0].message

            # ── Tool calls? ───────────────────────────────────────────
            if assistant_message.tool_calls:
                messages.append(assistant_message)

                for tool_call in assistant_message.tool_calls:
                    tool_result = self._execute_tool(
                        tool_call,
                        scenario=scenario,
                    )
                    messages.append({
                        "role":        "tool",
                        "tool_call_id": tool_call.id,
                        "content":     json.dumps(tool_result),
                    })

                # TOOL STATUS is already logged per-call inside _execute_tool.
                # Just note that we are looping back.
                logger.info("  LLM NEXT DECISION: looping back to LLM …")
                _log_divider()
                continue

            # ── Final answer ──────────────────────────────────────────
            final_answer = assistant_message.content or "(No response from LLM)"
            _log_section("FINAL RESPONSE")
            logger.info("%s", final_answer)
            _log_section("END")
            return final_answer

        # Exceeded max_iterations
        logger.warning(
            "Max iterations (%d) reached without a final answer.", max_iter
        )
        _log_section("END — MAX ITERATIONS REACHED")
        return (
            f"Agent reached the maximum of {max_iter} iterations without "
            "producing a final answer. This trajectory has been recorded."
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _call_llm(self, messages: list) -> object | None:
        """Send messages to Groq and return the raw response, or None on error."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=TOOL_SCHEMAS,
                tool_choice="auto",
                temperature=0,
            )
            msg = response.choices[0].message
            if msg.tool_calls:
                names = [tc.function.name for tc in msg.tool_calls]
                logger.info("  LLM TOOL DECISION : %s", names)
            else:
                logger.info("  LLM TOOL DECISION : (no tool call — final answer)")
            return response

        except RateLimitError as exc:
            logger.error("LLM rate limit exceeded: %s", exc)
        except APIConnectionError as exc:
            logger.error("LLM connection error: %s", exc)
        except APIError as exc:
            logger.error("LLM API error (status %s): %s", exc.status_code, exc)
        except Exception as exc:          # noqa: BLE001
            logger.error("Unexpected LLM error: %s", exc)
        return None

    def _execute_tool(
        self,
        tool_call,
        scenario: ScenarioConfig | None = None,
    ) -> dict:
        """
        Dispatch a single tool call with optional failure injection.

        The ToolFailureConfig (if any) is passed as `_scenario` to the tool
        function.  It is never part of the LLM-visible argument schema.
        """
        tool_name = tool_call.function.name
        raw_args  = tool_call.function.arguments

        logger.info("  TOOL NAME  : %s", tool_name)
        logger.info("  TOOL INPUT : %s", raw_args)

        # ── Validate tool name ────────────────────────────────────────
        if tool_name not in TOOL_REGISTRY:
            result = {
                "status": "error",
                "error": f"Unknown tool '{tool_name}'.",
                "available_tools": list(TOOL_REGISTRY.keys()),
            }
            logger.warning("  TOOL OUTPUT: %s", result)
            return result

        # ── Parse arguments ───────────────────────────────────────────
        try:
            args: dict = json.loads(raw_args)
        except json.JSONDecodeError as exc:
            result = {
                "status": "error",
                "error": f"Invalid JSON arguments for '{tool_name}': {exc}",
            }
            logger.warning("  TOOL OUTPUT: %s", result)
            return result

        # ── Inject scenario config ────────────────────────────────────
        tool_config: ToolFailureConfig | None = (
            scenario.get_tool_config(tool_name) if scenario else None
        )
        if tool_config is not None:
            args["_scenario"] = tool_config

        # ── Execute ───────────────────────────────────────────────────
        try:
            result = TOOL_REGISTRY[tool_name](**args)
        except TypeError as exc:
            result = {
                "status": "error",
                "error": f"Invalid arguments for '{tool_name}': {exc}",
                "received": {k: v for k, v in args.items() if not k.startswith("_")},
            }
            logger.warning("  TOOL OUTPUT: %s", result)
            return result
        except Exception as exc:          # noqa: BLE001
            result = {
                "status": "error",
                "error": f"Tool '{tool_name}' raised an unexpected error: {exc}",
            }
            logger.error("  TOOL OUTPUT: %s", result)
            return result

        # ── Log result ────────────────────────────────────────────────
        status_label = self._status_label(result)
        logger.info(
            "  TOOL OUTPUT:\n%s",
            json.dumps(result, indent=4, ensure_ascii=False),
        )
        logger.info("  TOOL STATUS: %s", status_label)
        return result

    @staticmethod
    def _status_label(result: dict) -> str:
        """Return a human-readable status label for a tool result dict."""
        status = result.get("status", "unknown")
        if status == "success":
            results_list = result.get("results", None)
            if results_list is not None and len(results_list) == 0:
                return "EMPTY_RESULT"
            return "SUCCESS"
        if status in ("failure", "no_flights_found", "city_not_found"):
            return "FAILURE"
        if status == "error":
            return "ERROR"
        return status.upper()
