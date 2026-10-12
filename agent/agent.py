
import json
import logging
import re

from agent.state import AgentState
from agent.executor import Executor
from agent.recovery import Recovery
from agent.verifier import Verifier
from agent.planner import Planner
from tools.approval_tools import ApprovalTools
from llm.client import LLMClient


logger = logging.getLogger(__name__)


class InvoiceAgent:
    def __init__(self, llm=None):
        self.llm = llm or LLMClient()
        self.planner = Planner(self.llm)
        self.executor = Executor()
        self.recovery = Recovery()
        self.verifier = Verifier()
        self.approval_tools = ApprovalTools()

    # ---------------------------------------------------------
    # State helpers
    # ---------------------------------------------------------

    @staticmethod
    def _initialize_state(state):
        state.data.setdefault("retry_count", 0)
        state.data.setdefault("unresolved_errors", [])
        state.data.setdefault("verification_passed", False)

    @staticmethod
    def _normalize(text):
        return re.sub(r"\s+", " ", str(text)).strip().lower()

    @staticmethod
    def _extract_invoice_id(text):
        match = re.search(
            r"\bINV-\d+\b",
            str(text),
            flags=re.IGNORECASE,
        )
        return match.group(0).upper() if match else None

    @staticmethod
    def _record_error(state, message):
        state.errors.append(str(message))
        state.observations.append(f"Error: {message}")

    # ---------------------------------------------------------
    # Planning
    # ---------------------------------------------------------

    def plan(self, state):
        try:
            # Planner.create_plan expects AgentState.
            plan = self.planner.create_plan(state)

            if not isinstance(plan, list):
                raise ValueError("Planner must return a list of steps.")

            state.plan = plan
            return plan

        except Exception as exc:
            self._record_error(state, f"Planning failed: {exc}")
            state.data["verification_passed"] = False
            state.success = False
            state.finished = False
            return []

    # ---------------------------------------------------------
    # Step classification
    # ---------------------------------------------------------

    @classmethod
    def _classify_step(cls, step):
        normalized = cls._normalize(step)
        compact = re.sub(r"[^a-z0-9]", "", normalized)

        # Never execute approval, payment, modification or deletion.
        unsafe_patterns = (
            r"\bapprove\b",
            r"\bpay\b",
            r"\bmodify\b",
            r"\bupdate\b",
            r"\bdelete\b",
        )

        if any(re.search(pattern, normalized) for pattern in unsafe_patterns):
            # A read-only eligibility check is allowed.
            if (
                "approval" in normalized
                and any(
                    word in normalized
                    for word in ("check", "eligibility", "eligible", "require")
                )
                and not any(
                    word in normalized
                    for word in ("approve", "pay", "modify", "update", "delete")
                )
            ):
                return "check_approval"

            return "unsafe"

        if (
            "approval" in normalized
            and any(
                word in normalized
                for word in ("check", "eligibility", "eligible", "require")
            )
        ):
            return "check_approval"

        if any(
            phrase in compact
            for phrase in (
                "findinvoice",
                "inspectinvoice",
                "openinvoice",
                "retrieveinvoice",
            )
        ):
            return "inspect_invoice"

        if any(
            phrase in compact
            for phrase in (
                "readinvoiceamount",
                "getinvoiceamount",
                "extractinvoiceamount",
                "retrieveinvoiceamount",
            )
        ):
            return "read_amount"

        if any(
            phrase in compact
            for phrase in (
                "reportinvoiceamount",
                "returninvoiceamount",
                "displayinvoiceamount",
                "provideinvoiceamount",
            )
        ):
            return "report_amount"

        return "unsupported"

    # ---------------------------------------------------------
    # Tool execution with retry
    # ---------------------------------------------------------

    def execute_with_retry(
        self,
        state,
        tool_name,
        max_retries=2,
        **arguments,
    ):
        """Execute a read-only tool, retrying temporary failures.

        ``max_retries`` counts retries after the initial attempt. Errors from
        failed attempts are retained for audit, but are marked recovered if a
        later attempt succeeds.
        """
        if tool_name != "inspect_invoice":
            raise ValueError(f"Unsupported tool: {tool_name}")

        state.data.setdefault("retry_count", 0)
        state.data.setdefault("unresolved_errors", [])
        last_error = None
        retry_errors = []

        for attempt in range(max_retries + 1):
            try:
                result = self.executor.execute_tool(
                    state,
                    tool_name,
                    **arguments,
                )
                state.data["last_result"] = result
                state.data["last_tool_error"] = None

                for error in retry_errors:
                    self.recovery.mark_recovered(state, error)
                if retry_errors:
                    state.observations.append(
                        f"Tool {tool_name} succeeded after "
                        f"{len(retry_errors)} retry attempt(s)."
                    )
                return result

            except Exception as exc:
                last_error = exc
                message = str(exc)

                if attempt < max_retries:
                    retry_errors.append(message)
                    state.errors.append(message)
                    state.data["retry_count"] += 1
                    state.data.setdefault("unresolved_errors", []).append(
                        message
                    )
                    logger.warning(
                        "Retrying %s: attempt %s/%s; error: %s",
                        tool_name,
                        attempt + 1,
                        max_retries,
                        message,
                    )

        message = str(last_error or "Tool execution failed.")
        state.data["last_tool_error"] = message
        self._record_error(state, message)
        state.data.setdefault("unresolved_errors", []).append(message)
        return None

    # Invoice content parsing
    # ---------------------------------------------------------

    @staticmethod
    def _parse_invoice_content(content):
        if isinstance(content, dict):
            return content

        if not isinstance(content, str):
            return {}

        content = content.strip()
        if not content:
            return {}

        try:
            parsed = json.loads(content)
            return parsed if isinstance(parsed, dict) else {}
        except (json.JSONDecodeError, TypeError):
            return {}

    @staticmethod
    def _to_number(value):
        if isinstance(value, bool) or value is None:
            return None

        if isinstance(value, (int, float)):
            return float(value)

        if isinstance(value, str):
            cleaned = (
                value.strip()
                .replace(",", "")
                .replace("₹", "")
                .replace("INR", "")
                .strip()
            )
            try:
                return float(cleaned)
            except ValueError:
                return None

        return None

    @staticmethod
    def _amount_from_text(text):
        if not isinstance(text, str):
            return None

        patterns = (
            r"\b(?:invoice\s+)?amount\b\s*[:=]\s*"
            r"(?:₹\s*|INR\s*)?([\d,]+(?:\.\d{1,2})?)",
            r"\btotal(?:\s+amount)?\b\s*[:=]\s*"
            r"(?:₹\s*|INR\s*)?([\d,]+(?:\.\d{1,2})?)",
        )

        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return float(match.group(1).replace(",", ""))

        return None

    def _get_invoice(self, state):
        # Reuse previously parsed invoice data.
        invoice = state.data.get("invoice")
        if isinstance(invoice, dict) and invoice:
            return invoice

        result = state.data.get("last_result", {})

        if not isinstance(result, dict):
            return {}

        # Support tools or tests returning the invoice directly.
        direct_invoice = result.get("invoice")
        if isinstance(direct_invoice, dict):
            invoice = direct_invoice
        else:
            invoice = self._parse_invoice_content(
                result.get("page_content", "")
            )

        if invoice:
            state.data["invoice"] = invoice

        return invoice

    def _extract_amount(self, state):
        invoice = self._get_invoice(state)

        # First check the structured invoice.
        amount = self._to_number(invoice.get("amount"))
        if amount is not None:
            return amount

        # Then check a directly returned amount.
        result = state.data.get("last_result", {})
        if isinstance(result, dict):
            amount = self._to_number(result.get("amount"))
            if amount is not None:
                return amount

            # Finally try labelled amount text from the webpage.
            amount = self._amount_from_text(
                str(result.get("page_content", ""))
            )
            if amount is not None:
                return amount

        return None

    def _get_amount(self, state):
        amount = self._to_number(state.data.get("invoice_amount"))

        if amount is None:
            amount = self._extract_amount(state)

        if amount is not None:
            state.data["invoice_amount"] = amount

        return amount

    # ---------------------------------------------------------
    # Verification
    # ---------------------------------------------------------

    def _verify(self, state):
        try:
            # Verifier.verify accepts state only.
            result = self.verifier.verify(state)
            return result is True
        except Exception as exc:
            self._record_error(state, f"Verification failed: {exc}")
            state.data["verification_passed"] = False
            state.success = False
            return False

    # ---------------------------------------------------------
    # Approval eligibility check (read-only)
    # ---------------------------------------------------------

    def _check_approval_eligibility(self, state, invoice_id):
        try:
            result = self.approval_tools.check_approval_eligibility(
                invoice_id=invoice_id
            )

            if not isinstance(result, dict):
                raise ValueError("Invalid approval eligibility result.")

            returned_id = result.get("invoice_id")
            if (
                isinstance(returned_id, str)
                and returned_id.upper() != invoice_id.upper()
            ):
                raise ValueError(
                    "Approval result belongs to a different invoice."
                )

            amount = self._to_number(result.get("amount"))
            if amount is None or amount < 0:
                raise ValueError("Invoice amount is missing or invalid.")

            if "human_approval_required" not in result:
                raise ValueError(
                    "Approval result is missing human_approval_required."
                )

            if "eligible_for_approval_review" not in result:
                raise ValueError(
                    "Approval result is missing eligible_for_approval_review."
                )

            state.data["approval_eligibility"] = result
            state.data["invoice_amount"] = amount
            state.data["verification_passed"] = True
            state.data["unresolved_errors"] = []

            if result["human_approval_required"]:
                state.observations.append(
                    f"Human approval is required for invoice {invoice_id}."
                )
            else:
                state.observations.append(
                    f"Human approval is not required for invoice {invoice_id}."
                )

            self._verify(state)
            state.finished = state.success
            return state.success

        except Exception as exc:
            self._record_error(state, str(exc))
            state.data["verification_passed"] = False
            state.success = False
            state.finished = True
            return False

    # ---------------------------------------------------------
    # Main agent workflow
    # ---------------------------------------------------------

    def run(self, goal):
        state = AgentState(user_goal=goal)
        self._initialize_state(state)

        plan = self.plan(state)

        if not plan:
            state.success = False
            state.finished = False
            return state

        step_types = [self._classify_step(step) for step in plan]

        # Reject unsafe/unsupported steps before making tool calls.
        if any(kind in ("unsafe", "unsupported") for kind in step_types):
            state.observations.append(
                "Workflow rejected: plan contains an unsafe or unsupported step."
            )
            state.data["verification_passed"] = False
            state.success = False
            state.finished = False
            return state

        invoice_id = self._extract_invoice_id(goal)

        if not invoice_id:
            for step in plan:
                invoice_id = self._extract_invoice_id(step)
                if invoice_id:
                    break

        if not invoice_id:
            self._record_error(state, "No valid invoice ID was provided.")
            state.data["verification_passed"] = False
            state.success = False
            state.finished = False
            return state

        # Read-only approval eligibility workflow.
        if "check_approval" in step_types:
            self._check_approval_eligibility(state, invoice_id)
            return state

        if "inspect_invoice" not in step_types:
            state.observations.append(
                "Workflow is incomplete: invoice inspection is missing."
            )
            state.data["verification_passed"] = False
            state.success = False
            state.finished = False
            return state

        # Inspect the invoice.
        result = self.execute_with_retry(
            state,
            "inspect_invoice",
            invoice_id=invoice_id,
        )

        if result is None:
            error_message = state.data.get("last_tool_error", "")

            if (
                "not found" in error_message.lower()
                or "404" in error_message
            ):
                state.data["verification_passed"] = False
                state.success = False
                state.finished = True
            else:
                state.data["verification_passed"] = False
                state.success = False
                state.finished = False

            return state

        if not isinstance(result, dict):
            self._record_error(state, "Invoice inspection returned invalid data.")
            state.data["verification_passed"] = False
            state.success = False
            state.finished = False
            return state

        state.data["last_result"] = result

        if result.get("http_status") == 404:
            self._record_error(
                state,
                f"Invoice {invoice_id} was not found.",
            )
            state.data["verification_passed"] = False
            state.success = False
            state.finished = True
            return state

        invoice = self._get_invoice(state)

        # Even if page content is not JSON, retain the result for
        # labelled-text amount extraction.
        if not invoice and "page_content" in result:
            state.data["invoice"] = {
                "invoice_id": invoice_id,
                "page_content": result["page_content"],
            }

        state.observations.append(
            f"Invoice {invoice_id} was inspected successfully."
        )

        # A find-only plan is not a completed amount-reporting workflow.
        if (
            "read_amount" not in step_types
            or "report_amount" not in step_types
        ):
            state.observations.append(
                "Workflow is incomplete: invoice amount was not read and reported."
            )
            state.data["verification_passed"] = False
            state.success = False
            state.finished = False
            return state

        amount = self._get_amount(state)

        if amount is None:
            self._record_error(
                state,
                f"Could not extract the amount for invoice {invoice_id}.",
            )
            state.data["verification_passed"] = False
            state.success = False
            state.finished = False
            return state

        state.data["invoice_amount"] = amount

        # Keep the exact report text consistent with the verifier.
        report = f"Report: The invoice amount is ₹{amount:,.2f}."
        state.observations.append(report)

        state.data["unresolved_errors"] = []
        state.data["verification_passed"] = True

        self._verify(state)

        if state.success:
            state.finished = True

        return state