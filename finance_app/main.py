import os

from dotenv import load_dotenv

load_dotenv()

APPROVAL_THRESHOLD = float(
    os.getenv("APPROVAL_THRESHOLD", "50000")
)

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from finance_app.database import (
    get_connection,
    initialize_database,
    seed_sample_invoices,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the database when the application starts."""

    initialize_database()
    seed_sample_invoices()
    yield


app = FastAPI(
    title="InvoicePilot Finance API",
    description="A local demo application for invoice processing.",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/")
def home():
    return {"message": "InvoicePilot Finance API is running"}


@app.get("/invoices")
def list_invoices():
    """Return all invoices."""

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT invoice_id, vendor, amount, status, description
            FROM invoices
            ORDER BY invoice_id
            """
        ).fetchall()

    return [dict(row) for row in rows]


@app.get("/invoices/{invoice_id}")
def get_invoice(invoice_id: str):
    """Return one invoice by its ID."""

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT invoice_id, vendor, amount, status, description
            FROM invoices
            WHERE invoice_id = ?
            """,
            (invoice_id,),
        ).fetchone()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail=f"Invoice {invoice_id} was not found",
        )

    return dict(row)


@app.post("/invoices/{invoice_id}/approve")
def approve_invoice(invoice_id: str, human_approved: bool = False):
    """Approve an invoice only when the required conditions are met."""

    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM invoices WHERE invoice_id = ?",
            (invoice_id,),
        ).fetchone()

        if row is None:
            raise HTTPException(
                status_code=404,
                detail=f"Invoice {invoice_id} was not found",
            )

        if row["status"] != "pending":
            raise HTTPException(
                status_code=409,
                detail=f"Invoice status is already {row['status']}",
            )

        if row["amount"] >= APPROVAL_THRESHOLD and not human_approved:
            raise HTTPException(
                status_code=403,
                detail=(
                    "Human approval is required for invoices "
                    f"of {APPROVAL_THRESHOLD:.2f} or more"
                ),
            )

        connection.execute(
            "UPDATE invoices SET status = 'approved' WHERE invoice_id = ?",
            (invoice_id,),
        )
        connection.commit()

    return {
        "message": "Invoice approved successfully",
        "invoice_id": invoice_id,
        "status": "approved",
    }