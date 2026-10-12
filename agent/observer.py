
from agent.state import AgentState


class Observer:
    """Records observations made during task execution."""

    def observe(self, state: AgentState, result: str) -> str:
        """Store and return the result of an action."""

        if not result.strip():
            result = "No result was returned by the action."

        state.observations.append(result)

        return result