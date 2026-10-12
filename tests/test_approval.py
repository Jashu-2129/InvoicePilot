import pytest

from tools.approval_tools import ApprovalTools


@pytest.fixture
def approval_tools():
    return ApprovalTools()


def test_invoice_below_threshold(approval_tools):
    result = approval_tools.check_approval_eligibility("INV-001")

    assert result["amount"] == 35000.0
    assert result["human_approval_required"] is False


def test_invoice_above_threshold(approval_tools):
    result = approval_tools.check_approval_eligibility("INV-004")

    assert result["amount"] == 75000.0
    assert result["human_approval_required"] is True
    assert result["eligible_for_approval_review"] is True


def test_missing_invoice(approval_tools):
    with pytest.raises(ValueError, match="was not found"):
        approval_tools.check_approval_eligibility("INV-999")