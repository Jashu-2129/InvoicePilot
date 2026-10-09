
from agent.agent import InvoiceAgent


class FakeLLM:
    def ask(self, prompt: str) -> str:
        return (
            '["Find invoice INV-001", '
            '"Read invoice amount", '
            '"Report invoice amount"]'
        )


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