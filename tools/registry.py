from tools.browser_tools import BrowserTools
from tools.approval_tools import ApprovalTools


class ToolRegistry:
    """Central registry for tools available to InvoicePilot."""

    def __init__(self):
        self.browser = BrowserTools()
        self.approval = ApprovalTools()

    def execute(self, tool_name: str, **arguments):
        """Execute an explicitly registered tool."""

        if tool_name == "inspect_invoice":
            return self.browser.inspect_invoice(
                arguments["invoice_id"]
            )

        if tool_name == "check_approval_eligibility":
            return self.approval.check_approval_eligibility(
                arguments["invoice_id"]
            )

        raise ValueError(f"Unknown tool: {tool_name}")