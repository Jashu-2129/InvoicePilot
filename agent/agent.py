import json

from agent.state import AgentState
from agent.planner import Planner
from agent.executor import Executor
from agent.observer import Observer
from agent.recovery import Recovery
from agent.verifier import Verifier
from utils.logger import get_logger


logger = get_logger(__name__)


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
                logger.info(
                    "Executing tool '%s' with arguments %s",
                    tool_name,
                    arguments,
                )

                result = self.executor.execute_tool(
                    state,
                    tool_name,
                    **arguments,
                )

                logger.info(
                    "Tool '%s' executed successfully",
                    tool_name,
                )

                return result

            except ValueError:
                # Missing invoices and invalid inputs are not retryable.
                raise

            except Exception as exc:
                should_retry = self.recovery.handle_error(
                    state,
                    str(exc),
                )

                logger.warning(
                    "Tool '%s' failed: %s",
                    tool_name,
                    exc,
                )

                if not should_retry:
                    logger.error(
                        "Retry limit reached for tool '%s'",
                        tool_name,
                    )
                    raise

                logger.info(
                    "Retrying tool '%s'",
                    tool_name,
                )

                self.observer.observe(
                    state,
                    f"Temporary tool error; retrying: {exc}",
                )

    def run(self, user_goal: str) -> AgentState:
        """Plan and execute supported invoice-processing tasks."""

        state = AgentState(user_goal=user_goal)

        logger.info("Starting agent for goal: %s", user_goal)

        try:
            # Step 1: Generate the plan.
            logger.info("Generating execution plan")
            self.planner.create_plan(state)

            logger.info(
                "Plan generated with %s steps",
                len(state.plan),
            )

            # Step 2: Execute supported plan steps.
            for step in state.plan:
                if state.finished:
                    break

                logger.info("Processing plan step: %s", step)
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
                        message = (
                            f"Could not find an invoice ID in: {step}"
                        )
                        logger.warning(message)
                        self.observer.observe(state, message)
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

                    self.observer.observe(
                        state,
                        approval_message,
                    )

                    logger.info(
                        "Checked approval eligibility for %s",
                        invoice_id,
                    )

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
                        message = (
                            f"Could not find an invoice ID in: {step}"
                        )
                        logger.warning(message)
                        self.observer.observe(state, message)
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

                    logger.info(
                        "Retrieved invoice %s",
                        invoice_id,
                    )

                # Read the amount from the retrieved invoice.
                elif (
                    "read invoice amount" in step_lower
                    or "read the invoice amount" in step_lower
                ):
                    invoice = state.data.get("invoice")

                    if invoice is None:
                        message = (
                            "Cannot read amount: "
                            "invoice has not been retrieved."
                        )
                        logger.warning(message)
                        self.observer.observe(state, message)
                        continue

                    amount = invoice.get("amount")

                    if (
                        not isinstance(amount, (int, float))
                        or isinstance(amount, bool)
                        or amount < 0
                    ):
                        message = (
                            "Invoice amount is missing or invalid."
                        )
                        logger.warning(message)
                        self.observer.observe(state, message)
                        continue

                    state.data["invoice_amount"] = amount

                    self.observer.observe(
                        state,
                        f"Invoice amount: \u20b9{amount:,.2f}",
                    )

                    logger.info("Invoice amount read successfully")

                # Report the amount.
                elif (
                    "report invoice amount" in step_lower
                    or "report the amount" in step_lower
                ):
                    amount = state.data.get("invoice_amount")

                    if amount is None:
                        message = (
                            "Cannot report amount: "
                            "amount has not been read."
                        )
                        logger.warning(message)
                        self.observer.observe(state, message)
                        continue

                    self.observer.observe(
                        state,
                        f"Report: The invoice amount is "
                        f"\u20b9{amount:,.2f}.",
                    )

                    logger.info("Invoice amount reported successfully")

                else:
                    message = f"Skipped unsupported plan step: {step}"
                    logger.warning(message)
                    self.observer.observe(state, message)

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

            logger.info(
                "Agent completed. Success=%s, Finished=%s",
                state.success,
                state.finished,
            )

        except ValueError as exc:
            self.recovery.handle_error(state, str(exc))

            logger.error("Agent stopped due to a known error: %s", exc)

            self.observer.observe(
                state,
                f"Error: {exc}",
            )

            state.data["verification_passed"] = False
            state.finished = True
            self.verifier.verify(state)

        except Exception as exc:
            logger.exception(
                "Unexpected error while running the agent"
            )

            self.observer.observe(
                state,
                f"Unexpected error: {exc}",
            )

            state.data["verification_passed"] = False
            state.finished = True
            self.verifier.verify(state)

        # Always return the state, including when an error occurs.
        return state