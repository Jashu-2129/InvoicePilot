import json
import re

from llm.client import LLMClient
from agent.state import AgentState


class Planner:
    """Creates an action plan for the AI agent."""

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def create_plan(self, state: AgentState) -> list[str]:
        """Create a plan using Gemini, with a safe local fallback."""

        prompt = f"""
You are the planning component of an invoice-processing AI agent.

Return only a valid JSON array of strings.
Do not include Markdown fences or extra text.
Do not invent invoice details.
Do not approve or pay invoices.
Preserve the exact wording of these steps for an invoice amount lookup:
1. Find invoice <INVOICE_ID>
2. Read invoice amount
3. Report invoice amount

Replace <INVOICE_ID> with the invoice ID from the user's goal.

User goal: {state.user_goal}
"""

        # Try the LLM first.
        try:
            response = self.llm.ask(prompt)
            print("PLANNER RAW RESPONSE:", repr(response))

            # Remove optional Markdown fences.
            response = re.sub(
                r"^```(?:json)?\s*|\s*```$",
                "",
                response.strip(),
                flags=re.IGNORECASE,
            ).strip()

            plan = json.loads(response)

            if not isinstance(plan, list) or not all(
                isinstance(step, str) for step in plan
            ):
                raise ValueError(
                    "The plan must be a JSON array of strings."
                )

            plan = [
                re.sub(r"\s+", " ", step).strip()
                for step in plan
            ]

            # Normalize the known invoice-amount steps.
            normalized_plan = []
            for step in plan:
                compact = re.sub(r"\s+", "", step).lower()

                if compact.startswith("findinvoice"):
                    invoice_id = re.search(
                        r"INV-\d+",
                        step,
                        flags=re.IGNORECASE,
                    )
                    if invoice_id:
                        normalized_plan.append(
                            f"Find invoice {invoice_id.group(0).upper()}"
                        )
                    else:
                        normalized_plan.append(step)

                elif compact == "readinvoiceamount":
                    normalized_plan.append("Read invoice amount")

                elif compact == "reportinvoiceamount":
                    normalized_plan.append("Report invoice amount")

                else:
                    normalized_plan.append(step)

            if not normalized_plan:
                raise ValueError("The planner returned an empty plan.")

            state.plan = normalized_plan
            return normalized_plan

        except Exception as exc:
            print(
                "PLANNER FALLBACK:",
                type(exc).__name__,
                str(exc),
            )
        # Local fallback for a read-only invoice amount request.
        match = re.search(
            r"\bINV-\d+\b",
            state.user_goal,
            flags=re.IGNORECASE,
        )
        goal_lower = state.user_goal.lower()

        asks_for_amount = "amount" in goal_lower and any(
            word in goal_lower
            for word in ("find", "report", "read")
        )

        # Explicitly reject affirmative requests to change invoices.
        requests_action = any(
            phrase in goal_lower
            for phrase in (
                "approve the invoice",
                "approve invoice",
                "pay the invoice",
                "pay invoice",
                "modify the invoice",
                "modify invoice",
                "update the invoice",
                "update invoice",
                "delete the invoice",
                "delete invoice",
            )
        )

        # These phrases explicity prohibit changes; don't mistake them
        # for requests to perform those actions.
        if any(
            phrase in goal_lower
            for phrase in (
                "do not approve",
                "do not pay",
                "do not modify",
                "do not update",
                "do not delete",
            )
        ):
            requests_action = False

        if match and asks_for_amount and not requests_action:
            invoice_id = match.group(0).upper()
            plan = [
                f"Find invoice {invoice_id}",
                "Read invoice amount",
                "Report invoice amount",
            ]
            state.plan = plan
            return plan

        raise ValueError(
            "Gemini planning failed and no safe local fallback applies."
        )