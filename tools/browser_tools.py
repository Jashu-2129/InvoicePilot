
from pathlib import Path

from playwright.sync_api import sync_playwright


class BrowserTools:
    """Browser operations for the InvoicePilot finance application."""

    def __init__(self):
        self.base_url = "http://127.0.0.1:8000"
        self.evidence_dir = Path("evidence")
        self.evidence_dir.mkdir(parents=True, exist_ok=True)

    def inspect_invoice(self, invoice_id: str) -> dict:
        """Open the invoice API in a browser and capture evidence."""

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page()

            try:
                url = f"{self.base_url}/invoices/{invoice_id}"
                response = page.goto(url, wait_until="domcontentloaded")

                screenshot_path = (
                    self.evidence_dir / f"{invoice_id}.png"
                )
                page.screenshot(path=str(screenshot_path))

                if response is None:
                    raise RuntimeError("The page returned no response.")

                if response.status == 404:
                    raise ValueError(f"Invoice {invoice_id} was not found.")

                if not response.ok:
                    raise RuntimeError(
                        f"Invoice request failed: HTTP {response.status}"
                    )

                invoice = page.locator("body").inner_text()

                return {
                    "invoice_id": invoice_id,
                    "http_status": response.status,
                    "page_content": invoice,
                    "screenshot": str(screenshot_path),
                }

            finally:
                browser.close()