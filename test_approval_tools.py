from tools.approval_tools import ApprovalTools

tools = ApprovalTools()

for invoice_id in ["INV-001", "INV-004", "INV-999"]:
    print(f"\nTesting {invoice_id}")

    try:
        result = tools.check_approval_eligibility(invoice_id)
        print("Amount:", result["amount"])
        print("Status:", result["status"])
        print(
            "Human approval required:",
            result["human_approval_required"],
        )
        print(
            "Eligible for approval review:",
            result["eligible_for_approval_review"],
        )
    except Exception as exc:
        print("Error:", exc)
