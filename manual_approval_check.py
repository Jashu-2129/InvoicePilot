from tools.approval_tools import ApprovalTools

tools = ApprovalTools()

try:
    result = tools.check_approval_eligibility("INV-004")

    print("\n--- APPROVAL ELIGIBILITY RESULT ---")
    print(f"Invoice ID: {result['invoice_id']}")
    print(f"Amount: ₹{result['amount']:,.2f}")
    print(f"Status: {result['status']}")
    print(f"Approval threshold: ₹{result['approval_threshold']:,.2f}")
    print(f"Human approval required: {result['human_approval_required']}")
    print(f"Eligible for approval review: {result['eligible_for_approval_review']}")

    assert result["human_approval_required"] is True
    print("\nPASS: Human approval requirement verified.")

except Exception as exc:
    print(f"\nTEST ERROR: {exc}")
