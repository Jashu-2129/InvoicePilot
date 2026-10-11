import json
import logging
import re
import time

from agent.state import AgentState
from agent.executor import Executor
from agent.recovery import Recovery
from agent.verifier import Verifier
from agent.planner import Planner
from tools.approval_tools import ApprovalTools

logger = logging.getLogger(__name__)


class InvoiceAgent:
    def __init__(
        self,
        llm,
        executor=None,
        recovery=None,
        verifier=None,
    ):
        self.llm = llm
        self.planner = Planner(llm)
        self.executor = executor or Executor()
        self.recovery = recovery or Recovery()
        self.verifier = verifier or Verifier()
        self.approval_tools = ApprovalTools()

    @staticmethod
    def _extract_invoice_id(user_goal):
        match = re.search(
            r"\bINV-\d+\b",
            user_goal,
            flags=re.IGNORECASE,
        )
        return match.group(0).upper() if match else None

    @staticmethod
    def _find_invoice(value):
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return None

        if isinstance(value, dict):
            invoice_id = value.get("invoice_id") or value.get("id")

            if invoice_id and any(
                key in value
                for key in ("amount", "total_amount", "total")
            ):
                return value

            page_content = value.get("page_content")
            if isinstance(page_content, str):
                found = InvoiceAgent._find_invoice(page_content)
                if found is not None:
                    return found

            for key in ("invoice", "data", "result"):
                if key in value:
                    found = InvoiceAgent._find_invoice(value[key])
                    if found is not None:
                        return found

        elif isinstance(value, list):
            for item in value:
                found = InvoiceAgent._find_invoice(item)
                if found is not None:
                    return found

        return None

    @staticmethod
    def _get_amount(invoice):
        if not isinstance(invoice, dict):
            return None

        for key in ("amount", "total_amount", "total"):
            if key in invoice:
                try:
                    amount = float(invoice[key])
                    return amount if amount >= 0 else None
                except (TypeError, ValueError):
                    return None

        return None

    def plan(self, state):
        try:
            plan = self.planner.create_plan(state)
            state.plan = plan
            logger.info("Agent plan: %s", plan)
            return plan
        except Exception as exc:
            error = f"Planning failed: {exc}"
            logger.exception(error)
            state.errors.append(error)
            state.data.setdefault("unresolved_errors", []).append(error)
            state.plan = []
            return []

    def execute_with_retry(self, state, tool_name, **arguments):
        retry_limit = max(1, self.recovery.max_retries)
        state.data.setdefault("retry_count", 0)

        for attempt in range(retry_limit):
            try:
                result = self.executor.execute_tool(
                    state,
                    tool_name,
                    **arguments,
                )

                if isinstance(result, dict) and result.get("error"):
                    raise RuntimeError(str(result["error"]))

                # A successful retry resolves errors from earlier attempts.
                state.data["unresolved_errors"] = []
                return result

            except Exception as exc:
                error = f"Tool {tool_name} failed: {exc}"
                state.errors.append(error)
                state.data.setdefault("unresolved_errors", []).append(error)

                # Count failed attempts, including the final failed attempt.
                state.data["retry_count"] += 1

                logger.warning(
                    "%s, attempt %s/%s",
                    error,
                    attempt + 1,
                    retry_limit,
                )

                if attempt + 1 < retry_limit:
                    time.sleep(min(2 ** attempt, 5))

        return None

    def _inspect_invoice(self, state, invoice_id):
        result = self.execute_with_retry(
            state,
            "inspect_invoice",
            invoice_id=invoice_id,
        )
        invoice = self._find_invoice(result)

        if not isinstance(invoice, dict):
            return None

        found_id = str(
            invoice.get("invoice_id", invoice.get("id", ""))
        ).upper()

        if found_id != invoice_id:
            return None

        return invoice

    def run(self, user_goal):
        state = AgentState(user_goal=user_goal)

        target_id = self._extract_invoice_id(user_goal)
        if not target_id:
            state.observations.append(
                "Unsupported operation: no invoice ID was found."
            )
            state.data["verification_passed"] = False
            state.success = False
            state.finished = False
            return state

        goal_lower = user_goal.lower()
        approval_query = (
            "approval" in goal_lower
            and any(
                word in goal_lower
                for word in (
                    "check",
                    "whether",
                    "eligibility",
                    "eligible",
                    "requires",
                    "require",
                )
            )
        )

        state.plan = self.plan(state)

        if not state.plan:
            state.observations.append(
                "Unable to create a valid execution plan."
            )
            state.data["verification_passed"] = False
            state.finished = True
            return state

        invoice = None
        amount = None
        invoice_retrieved = False
        amount_read = False
        reported = False
        approval_checked = False

        for step in state.plan:
            step_lower = re.sub(r"\s+", " ", step.lower()).strip()
            compact_step = re.sub(r"\s+", "", step_lower)

            if approval_query and (
                "approval" in step_lower or "eligible" in step_lower
            ):
                try:
                    eligibility = (
                        self.approval_tools.check_approval_eligibility(
                            target_id
                        )
                    )
                    state.data["approval_eligibility"] = eligibility
                    state.data["invoice_id"] = target_id
                    state.observations.append(
                        f"Approval eligibility checked for {target_id}. "
                        "Human approval is required when the invoice "
                        "amount meets the configured threshold."
                    )
                    approval_checked = True

                except Exception as exc:
                    error = f"Could not check approval eligibility: {exc}"
                    state.errors.append(error)
                    state.data.setdefault(
                        "unresolved_errors", []
                    ).append(error)
                    state.observations.append(error)

                continue

            if any(
                phrase in step_lower
                for phrase in (
                    "find invoice",
                    "retrieve invoice",
                    "inspect invoice",
                    "fetch invoice",
                )
            ):
                invoice = self._inspect_invoice(state, target_id)

                if invoice is not None:
                    invoice_retrieved = True
                    state.data["invoice"] = invoice
                    state.data["invoice_id"] = target_id
                    state.observations.append(
                        f"Retrieved invoice {target_id}."
                    )
                else:
                    invoice_retrieved = False
                    state.observations.append(
                        f"Invoice {target_id} was not found or "
                        "its details were invalid."
                    )

            elif compact_step in (
                "readinvoiceamount",
                "extractinvoiceamount",
            ):
                if not invoice_retrieved:
                    state.observations.append(
                        "Cannot read the amount before retrieving "
                        "the invoice."
                    )
                    continue

                amount = self._get_amount(invoice)

                if amount is not None:
                    amount_read = True
                    state.data["invoice_amount"] = amount
                    state.data["amount"] = amount
                    state.observations.append(
                        f"Invoice amount: ₹{amount:,.2f}."
                    )
                else:
                    state.observations.append(
                        "The invoice amount is missing or invalid."
                    )

            elif compact_step == "reportinvoiceamount":
                if amount_read:
                    reported = True
                    state.observations.append(
                        f"Invoice {target_id} amount is ₹{amount:,.2f}."
                    )
                else:
                    state.observations.append(
                        "Cannot report the amount because it has "
                        "not been read successfully."
                    )

            else:
                state.observations.append(
                    f"Skipped unsupported plan step: {step}"
                )

        workflow_checks_passed = (
            invoice_retrieved
            and amount_read
            and reported
            and invoice is not None
            and str(
                invoice.get("invoice_id", invoice.get("id", ""))
            ).upper() == target_id
            and amount is not None
        )

        if approval_query:
            workflow_checks_passed = approval_checked

        state.data["invoice_id"] = target_id
        state.data["verification_passed"] = bool(
            workflow_checks_passed
        )

        try:
            verification_passed = self.verifier.verify(state)
        except Exception as exc:
            logger.exception("Verification failed")
            state.errors.append(f"Verification failed: {exc}")
            state.data["verification_passed"] = False
            verification_passed = False

        state.data["verification_passed"] = verification_passed
        state.success = verification_passed

        # Unsupported or incomplete plans remain unfinished so the
        # caller can distinguish incomplete work from completed failure.
        if verification_passed:
            state.finished = True
        elif any(
            observation.startswith("Skipped unsupported plan step:")
            for observation in state.observations
        ):
            state.finished = False
        else:
            state.finished = True

        return state