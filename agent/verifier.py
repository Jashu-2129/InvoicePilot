
from agent.state import AgentState


class Verifier:
    """Checks whether the agent's task has succeeded."""

    def verify(self, state: AgentState) -> bool:
        """Determine success from an explicit verification result."""

        verified = state.data.get("verification_passed", False)

        if verified is True:
            state.success = True
            state.finished = True
            return True

        state.success = False
        return False