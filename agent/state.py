from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentState:
    """Stores the current state of the AI agent."""

    user_goal: str

    current_step: int = 0
    plan: list[str] = field(default_factory=list)
    observations: list[str] = field(default_factory=list)
    actions_taken: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    success: bool = False
    finished: bool = False

    data: dict[str, Any] = field(default_factory=dict)