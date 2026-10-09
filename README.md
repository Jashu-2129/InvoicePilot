# InvoicePilot AI Worker

InvoicePilot is a beginner-friendly AI-assisted invoice processing project built with Python, FastAPI, Playwright, and Google Gemini.

The project demonstrates how an AI agent can create a plan, inspect an invoice, retrieve its amount, check approval eligibility, and verify whether its task was completed successfully.

## Features

- **AI planning:** Uses an LLM interface to generate a sequence of task steps.
- **Invoice inspection:** Uses Playwright to access invoice information through the local API and capture evidence.
- **Approval eligibility:** Checks invoice status and whether human approval is required based on a configurable threshold.
- **Agent workflow:** Separates planning, execution, observation, recovery, and verification into components.
- **Automated tests:** Uses pytest and a fake LLM for tests that do not require Gemini API credits.
- **Local invoice database:** Stores sample invoice records using SQLite.

## Technology Stack

- Python
- FastAPI
- Google Gemini API (`google-genai`)
- Playwright
- SQLite
- Requests
- pytest

## Project Structure

```text
InvoicePilot/
├── agent/                 # Agent workflow components
├── evidence/              # Captured invoice inspection evidence
├── finance_app/           # FastAPI application and database
├── invoices/              # Invoice-related files
├── llm/                   # LLM client wrapper
├── logs/                  # Log directory
├── tests/                 # Automated tests
├── tools/                 # Browser, invoice, and approval tools
├── .env.example           # Environment variable template
├── .gitignore
├── requirements.txt
└── README.md
```

## Setup

### 1. Create and activate a virtual environment

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```powershell
python -m pip install -r requirements.txt
python -m playwright install chromium
```

### 3. Configure environment variables

Copy the example environment file:

```powershell
Copy-Item .env.example .env
```

Open `.env` and configure your Gemini API key and the required settings. Never commit `.env` or share your API key.

The project uses `FINANCE_APP_URL` to locate the local finance application and `APPROVAL_THRESHOLD` to configure the approval threshold.

### 4. Start the application

```powershell
python -m uvicorn finance_app.main:app --reload
```

Open the local API documentation at:

http://127.0.0.1:8000/docs

Keep the server running while executing tests that access the application.

## Run Automated Tests

In a second terminal, activate your environment and run:

```powershell
python -m pytest -v
```

The automated tests use a fake LLM for agent and planner checks, avoiding Gemini API calls in those tests.

## Approval Workflow

The approval tool reports whether an invoice is pending and whether its amount meets or exceeds the configured human-approval threshold.

The tool checks eligibility; it does not itself approve or pay invoices.

The local application includes a demonstration approval endpoint. Its query parameter is not production-grade authentication, so this project must not be used to authorize real payments.

## Current Limitations

- The agent currently supports a limited set of plan steps rather than arbitrary natural-language tasks.
- Playwright inspects the local invoice API response; it does not automate a complete graphical finance application.
- The recovery component records errors and retry counts, but the agent does not yet implement a complete retry loop.
- The sample approval workflow is intended for demonstration and testing, not production financial operations.

## Security

- Keep API keys in `.env`.
- Do not commit credentials, local database files, or other secrets.
- Human approval and payment authorization require proper authentication and authorization before production use.

## Project Status

This is a learning and internship-demonstration project. Its components and tests demonstrate a basic AI-assisted invoice workflow, with further development needed for production use.
 