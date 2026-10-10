from unittest.mock import Mock

from agent.agent import InvoiceAgent


class FakeLLM:
    def ask(self, prompt: str) -> str:
        return (
            '["Find invoice INV-001", '
            '"Read invoice amount", '
            '"Report invoice amount"]'
        )


class ApprovalFakeLLM:
    def ask(self, prompt: str) -> str:
        return '["Check approval eligibility for INV-004"]'


class MissingInvoiceFakeLLM:
    def ask(self, prompt: str) -> str:
        return '["Find invoice INV-999"]'


class IncompleteWorkflowFakeLLM:
    def ask(self, prompt: str) -> str:
        return '["Perform an unsupported operation"]'


def test_agent_inspects_and_reports_invoice():
    agent = InvoiceAgent(FakeLLM())

    state = agent.run(
        "Find invoice INV-001 and report its amount"
    )

    assert state.success is True
    assert state.finished is True
    assert state.data["invoice"]["invoice_id"] == "INV-001"
    assert state.data["invoice_amount"] == 35000.0
    assert any(
        "₹35,000.00" in observation
        for observation in state.observations
    )


def test_agent_checks_approval_eligibility():
    agent = InvoiceAgent(ApprovalFakeLLM())

    state = agent.run(
        "Check whether invoice INV-004 requires human approval"
    )

    assert state.success is True
    assert state.finished is True

    result = state.data["approval_eligibility"]

    assert result["invoice_id"] == "INV-004"
    assert result["amount"] == 75000.0
    assert result["human_approval_required"] is True
    assert result["eligible_for_approval_review"] is True

    assert any(
        "Human approval is required" in observation
        for observation in state.observations
    )


def test_agent_handles_missing_invoice():
    agent = InvoiceAgent(MissingInvoiceFakeLLM())

    state = agent.run("Find invoice INV-999")

    assert state.success is False
    assert state.finished is True
    assert any(
        "INV-999 was not found" in observation
        for observation in state.observations
    )


def test_agent_does_not_succeed_on_incomplete_workflow():
    agent = InvoiceAgent(IncompleteWorkflowFakeLLM())

    state = agent.run("Perform an unsupported operation")

    assert state.success is False
    assert state.finished is False
    assert state.data["verification_passed"] is False


def test_agent_retries_temporary_tool_failure():
    agent = InvoiceAgent(Mock())

    # Simulate a temporary failure followed by a successful tool call.
    agent.executor.execute_tool = Mock(
        side_effect=[
            RuntimeError("Temporary connection error"),
            {
                "http_status": 200,
                "page_content": "{}",
            },
        ]
    )

    from agent.state import AgentState

    state = AgentState(user_goal="Find invoice INV-001")

    result = agent.execute_with_retry(
        state,
        "inspect_invoice",
        invoice_id="INV-001",
    )

    assert result["http_status"] == 200
    assert agent.executor.execute_tool.call_count == 2
    assert state.data["retry_count"] == 1
    assert len(state.errors) == 1
