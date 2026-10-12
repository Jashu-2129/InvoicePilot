# InvoicePilot AI Worker

InvoicePilot is a Python-based, AI-assisted invoice processing project built with FastAPI, Playwright, SQLite, and Google Gemini.

The project demonstrates an invoice-agent workflow that plans a task, retrieves invoice information, checks approval eligibility, records observations, and verifies whether the requested task was completed.

## Features

* **AI-assisted planning:** Uses an LLM client to generate task steps, with a fallback when planning fails.
* **Invoice inspection:** Retrieves invoice information from the local finance application and supports browser-based inspection through Playwright.
* **Approval eligibility:** Checks invoice status and whether human approval is required based on a configurable threshold.
* **Agent workflow:** Organizes planning, execution, observations, error handling, and task verification.
* **Local database:** Stores sample invoice records using SQLite.
* **Automated testing:** Uses pytest and test doubles to verify application and agent behavior without requiring a live Gemini API call for every test.

## Technology Stack

* Python
* FastAPI
* Google Gemini API (`google-genai`)
* Playwright
* SQLite
* Requests
* pytest

## Project Structure

```text
InvoicePilot/
├── agent/                 # Agent workflow and planning
├── evidence/              # Invoice inspection evidence
├── finance_app/           # FastAPI application and database
├── invoices/              # Invoice-related files
├── llm/                   # LLM client wrapper
├── logs/                  # Log directory
├── tests/                 # Automated tests
├── tools/                 # Invoice, browser, and approval tools
├── utils/                 # Shared utilities and logging
├── .env.example           # Environment variable template
├── .gitignore
├── requirements.txt
└── README.md
```

## Prerequisites

* Python installed and available from PowerShell.
* A Google Gemini API key for live LLM requests.
* Git, if you want to clone the repository.

## Setup

### 1. Clone the repository

If you have not already cloned the project:

```powershell
git clone https://github.com/Jashu-2129/InvoicePilot.git
cd InvoicePilot
```

If you already have the project locally, open its existing folder instead.

### 2. Create and activate a virtual environment

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
python -m pip install -r requirements.txt
python -m playwright install chromium
```

### 4. Configure environment variables

Create your local environment file:

```powershell
Copy-Item .env.example .env
```

Open `.env` and configure the required values, including your Gemini API key and application settings.

The project uses `FINANCE_APP_URL` to locate the local finance application and `APPROVAL_THRESHOLD` to configure the approval threshold.

**Security:** Never commit `.env`, API keys, or other secrets to GitHub.

## Run the Application

Start the FastAPI server from the project root:

```powershell
python -m uvicorn finance_app.main:app --reload
```

Open the interactive API documentation:

http://127.0.0.1:8000/docs

Keep the server running while testing endpoints that require the application to be available.

### Example: Retrieve an Invoice

With the server running, open:

http://127.0.0.1:8000/invoices/INV-001

The sample invoice `INV-001` is expected to contain information such as its vendor, amount, status, and description, based on the local application data.

You can also query it from a second PowerShell terminal:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/invoices/INV-001
```

## Run Automated Tests

Activate your virtual environment, navigate to the project root, and run:

```powershell
python -m pytest -v --ignore=test_gemini_json.py
```

The regular test suite uses test doubles for relevant agent and planner tests, so those tests do not need to make a live Gemini API request.

### Live Gemini Integration Test

The separate `test_gemini_json.py` test calls the Gemini API. Run it only when your API key, model access, and available quota have been verified.

```powershell
python -m pytest -v test_gemini_json.py
```

Live integration tests can fail because of API quota limits, network errors, or model availability. Such failures should be distinguished from failures in the local automated test suite.

## Approval Workflow

The approval tool checks whether an invoice is eligible for approval based on its status and the configured human-approval threshold.

Checking eligibility is not the same as approving or paying an invoice. The demonstration approval endpoint is not production-grade authentication or authorization and must not be used to authorize real payments.

## LLM Fallback Behavior

The agent includes fallback behavior for situations in which LLM planning fails. For example, a Gemini quota error can prevent a live request from succeeding, while a local fallback may still construct a supported plan.

A successful fallback workflow does not prove that the task plan was generated by Gemini. Live LLM behavior and fallback behavior should be tested and reported separately.

## Current Limitations

* The agent supports a limited set of invoice-related task steps rather than arbitrary natural-language tasks.
* Playwright-based inspection is intended for the local demonstration application; it does not automate a complete production finance interface.
* LLM requests depend on API availability, credentials, and quota limits.
* The approval workflow is for demonstration and testing, not production financial operations.

## Security Considerations

* Keep API keys and other credentials in `.env`.
* Do not commit secrets or sensitive invoice data.
* Use appropriate authentication and authorization before exposing application endpoints.
* Require a secure, auditable human-approval process before any real financial action.

## Project Status

InvoicePilot is a learning and internship-demonstration project. It brings together an API, a local invoice database, an LLM client, agent planning, invoice tools, and automated tests to demonstrate a basic AI-assisted invoice workflow.

Further validation, security controls, and production-grade integrations would be required before using it in a real financial environment.