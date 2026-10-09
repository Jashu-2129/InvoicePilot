from agent.planner import Planner
from agent.state import AgentState


class FakeLLM:
    def ask(self, prompt: str) -> str:
        return (
            '["Find invoice INV-001", '
            '"Read the invoice amount", '
            '"Report the amount"]'
        )


def test_planner_creates_and_saves_plan():
    state = AgentState(
        "Find invoice INV-001 and report its amount"
    )

    planner = Planner(FakeLLM())
    plan = planner.create_plan(state)

    assert len(plan) == 3
    assert plan[0] == "Find invoice INV-001"
    assert state.plan == plan
