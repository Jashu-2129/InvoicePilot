
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