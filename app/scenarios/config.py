"""
scenarios/config.py

ScenarioConfig — a plain dataclass that describes how a single test scenario
should behave.  The agent reads this config and injects it into tool calls
so that tool behavior is controlled deterministically without touching the
tool's normal business logic.

No randomness.  No real APIs.  100% reproducible.
"""

from dataclasses import dataclass, field


@dataclass
class ToolFailureConfig:
    """
    Controls how many times a specific tool should fail before succeeding.

    Attributes:
        tool_name:          Name of the tool this config applies to.
        fail_times:         How many consecutive calls should return a failure
                            response before allowing a success.  0 = never fail.
        always_fail:        If True, the tool always returns failure regardless
                            of fail_times.  Used for repeated-failure and
                            impossible-task scenarios.
        empty_result:       If True, the tool returns status="success" but with
                            an empty results list.  Used for empty-result and
                            loop scenarios.
        failure_message:    The error message to embed in the failure response.
    """
    tool_name: str
    fail_times: int = 0
    always_fail: bool = False
    empty_result: bool = False
    failure_message: str = "Tool encountered a temporary error. Please retry."


@dataclass
class ScenarioConfig:
    """
    Top-level scenario descriptor consumed by the Agent and main.py.

    Attributes:
        name:               Short CLI key, e.g. "recovery".
        description:        One-line human description shown in the banner.
        task:               The natural-language user task to send to the agent.
        tool_configs:       List of ToolFailureConfig entries.  The agent
                            looks up the matching config by tool_name before
                            each call.
        max_iterations:     Override the agent's default iteration cap.
                            Useful for loop scenarios where we want to observe
                            several failed attempts.
        phase:              "1" or "2" — used in the banner.
    """
    name: str
    description: str
    task: str
    tool_configs: list[ToolFailureConfig] = field(default_factory=list)
    max_iterations: int = 5
    phase: str = "2"

    def get_tool_config(self, tool_name: str) -> ToolFailureConfig | None:
        """Return the ToolFailureConfig for the named tool, or None."""
        for tc in self.tool_configs:
            if tc.tool_name == tool_name:
                return tc
        return None
