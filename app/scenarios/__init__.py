"""
scenarios/__init__.py

Exports the ScenarioConfig dataclass and all named scenario instances.
"""

from app.scenarios.config import ScenarioConfig
from app.scenarios.definitions import SCENARIOS, get_scenario

__all__ = ["ScenarioConfig", "SCENARIOS", "get_scenario"]
