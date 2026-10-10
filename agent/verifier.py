from agent.state import AgentState


class Verifier:
    """Checks whether the agent's task has succeeded."""

    def verify(self, state: AgentState) -> bool:
        """Verify that the requested workflow completed successfully."""

        verified = state.data.get("verification_passed", False)

        # A failed or incomplete task must never be marked successful.
        if verified is not True:
            state.success = False
            return False

        # Do not report success if the agent recorded an error.
        if state.errors:
            state.success = False
            return False

        # Only mark the task successful after all checks pass.
        state.success = True
        state.finished = True

        return True
