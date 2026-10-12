import json
import os
from pathlib import Path

import requests
from playwright.sync_api import sync_playwright


class BrowserTools:
    """Inspect invoices with Playwright, falling back to HTTP if Chromium is absent."""

    def __init__(self):
        self.base_url = os.getenv(
            "FINANCE_APP_URL",
            "http://127.0.0.1:8000",
        ).rstrip("/")
        self.evidence_dir = Path("evidence")
        self.evidence_dir.mkdir(parents=True, exist_ok=True)

    def _http_inspect(self, invoice_id: str) -> dict:
        """Read the invoice endpoint without a browser (portable fallback)."""
        response = requests.get(
            f"{self.base_url}/invoices/{invoice_id}",
            timeout=10,
        )
        if response.status_code == 404:
            raise ValueError(f"Invoice {invoice_id} was not found.")
        response.raise_for_status()
        invoice = response.json()
        return {
            "invoice_id": invoice_id,
            "http_status": response.status_code,
            "page_content": json.dumps(invoice, ensure_ascii=False),
            "screenshot": None,
            "inspection_mode": "http_fallback",
        }

    def inspect_invoice(self, invoice_id: str) -> dict:
        """Open the invoice API in a browser and capture evidence.

        If Chromium is not installed, use the same read-only API endpoint
        directly so local tests and basic workflows can still run.
        """
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                try:
                    page = browser.new_page()
                    url = f"{self.base_url}/invoices/{invoice_id}"
                    response = page.goto(url, wait_until="domcontentloaded")

                    if response is None:
                        raise RuntimeError("The page returned no response.")

                    screenshot_path = (
                        self.evidence_dir / f"{invoice_id}.png"
                    )
                    page.screenshot(path=str(screenshot_path))

                    if response.status == 404:
                        raise ValueError(
                            f"Invoice {invoice_id} was not found."
                        )
                    if not response.ok:
                        raise RuntimeError(
                            f"Invoice request failed: HTTP {response.status}"
                        )

                    return {
                        "invoice_id": invoice_id,
                        "http_status": response.status,
                        "page_content": page.locator("body").inner_text(),
                        "screenshot": str(screenshot_path),
                        "inspection_mode": "playwright",
                    }
                finally:
                    browser.close()
        except ValueError:
            # Preserve business errors such as an invoice 404.
            raise
        except Exception as exc:
            # Fallback only if browser inspection itself cannot run. The
            # HTTP request still raises clear errors for API/network issues.
            try:
                result = self._http_inspect(invoice_id)
                result["browser_fallback_reason"] = str(exc)
                return result
            except Exception:
                raise
