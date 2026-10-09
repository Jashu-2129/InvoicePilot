
import json

from llm.client import LLMClient
from agent.state import AgentState


class Planner:
    """Creates an action plan for the AI agent."""

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def create_plan(self, state: AgentState) -> list[str]:
        """Convert the user's goal into a list of steps."""

        prompt = f"""
You are the planning component of an invoice-processing AI agent.

Break the user's goal into a short sequence of clear steps.

Rules:
- Return only a JSON array of strings.
- Do not claim that any action has already been performed.
- Do not invent invoice details.
- Do not approve or pay invoices in the planning stage.
- Keep the steps specific and easy to execute.

User goal: {state.user_goal}
"""

        response = self.llm.ask(prompt)

        try:
            plan = json.loads(response)
        except json.JSONDecodeError as exc:
            raise ValueError(
                "The LLM did not return valid JSON for the plan."
            ) from exc

        if not isinstance(plan, list) or not all(
            isinstance(step, str) for step in plan
        ):
            raise ValueError(
                "The plan must be a JSON array containing only strings."
            )

        if not plan:
            raise ValueError("The planner returned an empty plan.")

        state.plan = plan
        return plan