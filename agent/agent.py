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

    def execute_with_retry(
        self,
        state: AgentState,
        tool_name: str,
        **arguments,
    ) -> dict:
        """Retry a tool call after unexpected temporary failures."""

        while True:
            try:
                return self.executor.execute_tool(
                    state,
                    tool_name,
                    **arguments,
                )

            except ValueError:
                # Missing invoices and invalid inputs are not retryable.
                raise

            except Exception as exc:
                should_retry = self.recovery.handle_error(
                    state,
                    str(exc),
                )

                if not should_retry:
                    raise

                self.observer.observe(
                    state,
                    f"Temporary tool error; retrying: {exc}",
                )

    def run(self, user_goal: str) -> AgentState:
        """Plan and execute supported invoice-processing tasks."""

        state = AgentState(user_goal=user_goal)

        try:
            # Step 1: Generate the plan.
            self.planner.create_plan(state)

            # Step 2: Execute supported plan steps.
            for step in state.plan:
                if state.finished:
                    break

                step_lower = step.lower()

                # Check invoice approval eligibility.
                if "check approval eligibility" in step_lower:
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

                    result = self.execute_with_retry(
                        state,
                        "check_approval_eligibility",
                        invoice_id=invoice_id,
                    )

                    state.data["approval_eligibility"] = result

                    amount = result["amount"]
                    status = result["status"]

                    if result["human_approval_required"]:
                        approval_message = (
                            f"Invoice {invoice_id} is "
                            f"\u20b9{amount:,.2f}. "
                            "Human approval is required."
                        )
                    else:
                        approval_message = (
                            f"Invoice {invoice_id} is "
                            f"\u20b9{amount:,.2f}. "
                            "Human approval is not required "
                            "by the threshold."
                        )

                    if not result["eligible_for_approval_review"]:
                        approval_message += (
                            f" Current status is '{status}'; "
                            "it is not eligible for approval review."
                        )

                    self.observer.observe(state, approval_message)

                # Find and inspect an invoice.
                elif (
                    "inspect" in step_lower
                    or "find invoice" in step_lower
                ):
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

                    result = self.execute_with_retry(
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

                    self.observer.observe(
                        state,
                        f"Retrieved invoice {invoice_id}.",
                    )

                # Read the amount from the retrieved invoice.
                elif (
                    "read invoice amount" in step_lower
                    or "read the invoice amount" in step_lower
                ):
                    invoice = state.data.get("invoice")

                    if invoice is None:
                        self.observer.observe(
                            state,
                            "Cannot read amount: invoice has not been retrieved.",
                        )
                        continue

                    amount = invoice.get("amount")

                    if (
                        not isinstance(amount, (int, float))
                        or isinstance(amount, bool)
                        or amount < 0
                    ):
                        self.observer.observe(
                            state,
                            "Invoice amount is missing or invalid.",
                        )
                        continue

                    state.data["invoice_amount"] = amount

                    self.observer.observe(
                        state,
                        f"Invoice amount: \u20b9{amount:,.2f}",
                    )

                # Report the amount.
                elif (
                    "report invoice amount" in step_lower
                    or "report the amount" in step_lower
                ):
                    amount = state.data.get("invoice_amount")

                    if amount is None:
                        self.observer.observe(
                            state,
                            "Cannot report amount: amount has not been read.",
                        )
                        continue

                    self.observer.observe(
                        state,
                        f"Report: The invoice amount is "
                        f"\u20b9{amount:,.2f}.",
                    )

                else:
                    self.observer.observe(
                        state,
                        f"Skipped unsupported plan step: {step}",
                    )

            # Step 3: Verify the requested workflow.
            observations = "\n".join(state.observations)

            amount_reported = (
                state.data.get("invoice") is not None
                and state.data.get("invoice_amount") is not None
                and "Report: The invoice amount is" in observations
            )

            approval_checked = (
                state.data.get("approval_eligibility") is not None
                and any(
                    "Human approval" in observation
                    for observation in state.observations
                )
            )

            state.data["verification_passed"] = (
                amount_reported or approval_checked
            )

            self.verifier.verify(state)

        except ValueError as exc:
            # Known errors, such as a missing invoice.
            self.recovery.handle_error(state, str(exc))
            self.observer.observe(state, f"Error: {exc}")

            state.data["verification_passed"] = False
            state.finished = True
            self.verifier.verify(state)

        except Exception as exc:
            # Unexpected errors after retries are exhausted.
            self.observer.observe(
                state,
                f"Unexpected error: {exc}",
            )

            state.data["verification_passed"] = False
            state.finished = True
            self.verifier.verify(state)

        return state