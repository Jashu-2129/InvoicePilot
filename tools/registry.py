from tools.browser_tools import BrowserTools
from tools.approval_tools import ApprovalTools


class ToolRegistry:
    """Central registry for explicitly permitted InvoicePilot tools."""

    ALLOWED_TOOLS = {
        "inspect_invoice",
        "check_approval_eligibility",
    }

    def __init__(self):
        self.browser = BrowserTools()
        self.approval = ApprovalTools()

    def execute(self, tool_name: str, **arguments):
        """Execute only registered tools."""

        if tool_name not in self.ALLOWED_TOOLS:
            raise ValueError(f"Unknown or disallowed tool: {tool_name}")

        invoice_id = arguments.get("invoice_id")
        if not isinstance(invoice_id, str):
            raise ValueError("A valid invoice_id is required.")

        if tool_name == "inspect_invoice":
            return self.browser.inspect_invoice(invoice_id)

        if tool_name == "check_approval_eligibility":
            return self.approval.check_approval_eligibility(invoice_id)

        raise ValueError(f"Unknown or disallowed tool: {tool_name}")
