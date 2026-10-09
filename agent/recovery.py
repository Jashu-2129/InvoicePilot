
import os

from dotenv import load_dotenv
from agent.state import AgentState

load_dotenv()


class Recovery:
    """Tracks failed actions and limits retry attempts."""

    def __init__(self):
        self.max_retries = int(os.getenv("MAX_RETRIES", "3"))

    def handle_error(self, state: AgentState, error: str) -> bool:
        """Record an error and decide whether retries remain."""

        state.errors.append(error)

        attempts = state.data.get("retry_count", 0) + 1
        state.data["retry_count"] = attempts

        if attempts >= self.max_retries:
            state.finished = True
            return False

        return True