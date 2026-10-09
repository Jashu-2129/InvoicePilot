import json

from agent.state import AgentState
from agent.planner import Planner
from agent.executor import Executor
from agent.observer import Observer
from agent.recovery import Recovery
from agent.verifier import Verifier


class InvoiceAgent:
    """Coordinates the components of the invoice-processing agent."""

    def __init__(self, llm):
        self.planner = Planner(llm)
        self.executor = Executor()
        self.observer = Observer()
        self.recovery = Recovery()
        self.verifier = Verifier()

    def run(self, user_goal: str) -> AgentState:
        """Plan, inspect an invoice, and report its amount."""

        state = AgentState(user_goal=user_goal)

        try:
            # Step 1: Generate the plan.
            self.planner.create_plan(state)

            # Step 2: Execute the supported steps.
            for step in state.plan:
                if state.finished:
                    break

                step_lower = step.lower()

                # Find and inspect an invoice.
                if "inspect" in step_lower or "find invoice" in step_lower:
                    words = step.replace(",", " ").split()

                    invoice_id = next(
                        (
                            word.strip(".,:;")
                            for word in words
                            if word.upper().startswith("INV-")
                        ),
                        None,
                    )

                    if invoice_id is None:
                        self.observer.observe(
                            state,
                            f"Could not find an invoice ID in: {step}",
                        )
                        continue

                    result = self.executor.execute_tool(
                        state,
                        "inspect_invoice",
                        invoice_id=invoice_id,
                    )

                    if result.get("http_status") != 200:
                        raise RuntimeError(
                            f"Invoice inspection failed: {invoice_id}"
                        )

                    invoice = json.loads(result["page_content"])

                    state.data["invoice"] = invoice
                    state.data["verification_passed"] = False

                    self.observer.observe(
                        state,
                        f"Retrieved invoice {invoice_id}.",
                    )

                # Read the amount from the retrieved invoice.
                elif "read invoice amount" in step_lower:
                    invoice = state.data.get("invoice")

                    if invoice is None:
                        self.observer.observe(
                            state,
                            "Cannot read amount: invoice has not been retrieved.",
                        )
                        continue

                    amount = invoice.get("amount")

                    if not isinstance(amount, (int, float)):
                        self.observer.observe(
                            state,
                            "Invoice amount is missing or invalid.",
                        )
                        continue

                    state.data["invoice_amount"] = amount

                    self.observer.observe(
                        state,
                        f"Invoice amount: ₹{amount:,.2f}",
                    )

                # Report the amount.
                elif "report invoice amount" in step_lower:
                    amount = state.data.get("invoice_amount")

                    if amount is None:
                        self.observer.observe(
                            state,
                            "Cannot report amount: amount has not been read.",
                        )
                        continue

                    self.observer.observe(
                        state,
                        f"Report: The invoice amount is ₹{amount:,.2f}.",
                    )

                else:
                    self.observer.observe(
                        state,
                        f"Skipped unsupported plan step: {step}",
                    )

            # Step 3: Verify that all required stages were completed.
            observations = "\n".join(state.observations)

            state.data["verification_passed"] = (
                state.data.get("invoice") is not None
                and state.data.get("invoice_amount") is not None
                and "Report: The invoice amount is" in observations
            )

            self.verifier.verify(state)

        except ValueError as exc:
            # Handle known errors, such as an invoice not being found.
            self.recovery.handle_error(state, str(exc))
            self.observer.observe(state, f"Error: {exc}")

            state.data["verification_passed"] = False
            state.finished = True
            self.verifier.verify(state)

        except Exception as exc:
            # Handle unexpected errors.
            self.recovery.handle_error(state, str(exc))
            self.observer.observe(
                state,
                f"Unexpected error: {exc}",
            )

            state.data["verification_passed"] = False
            state.finished = True
            self.verifier.verify(state)

        return state


