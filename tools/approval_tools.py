import os

import requests
from dotenv import load_dotenv

load_dotenv()


class ApprovalTools:
    """Tools for checking invoice approval eligibility."""

    def __init__(self):
        self.base_url = os.getenv(
            "FINANCE_APP_URL",
            "http://127.0.0.1:8000",
        )
        self.approval_threshold = float(
            os.getenv("APPROVAL_THRESHOLD", "50000")
        )

    def check_approval_eligibility(self, invoice_id: str) -> dict:
        """Check invoice details and whether human approval is required.

        This method does not approve or pay an invoice.
        """

        response = requests.get(
            f"{self.base_url}/invoices/{invoice_id}",
            timeout=10,
        )

        if response.status_code == 404:
            raise ValueError(f"Invoice {invoice_id} was not found.")

        response.raise_for_status()
        invoice = response.json()

        amount = invoice.get("amount")

        if not isinstance(amount, (int, float)) or amount < 0:
            raise ValueError("Invoice amount is missing or invalid.")

        return {
            "invoice_id": invoice["invoice_id"],
            "amount": amount,
            "status": invoice["status"],
            "approval_threshold": self.approval_threshold,
            "human_approval_required": (
                amount >= self.approval_threshold
            ),
            "eligible_for_approval_review": (
                invoice["status"] == "pending"
            ),
        }