
from agent.planner import Planner
from agent.state import AgentState


class FakeLLM:
    """Simulates an LLM without making an API request."""

    def ask(self, prompt: str) -> str:
        return '["Find invoice INV-001", "Read the invoice amount", "Report the amount"]'


state = AgentState(
    "Find invoice INV-001 and report its amount"
)

planner = Planner(FakeLLM())
plan = planner.create_plan(state)

print("Generated plan:", plan)
print("Saved correctly:", state.plan == plan)