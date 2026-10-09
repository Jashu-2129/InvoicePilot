
import sqlite3
from pathlib import Path

DATABASE_PATH = Path(__file__).resolve().parent / "invoices.db"


def get_connection():
    """Open a connection to the invoice database."""

    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    """Create the invoices table if it does not exist."""

    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS invoices (
                invoice_id TEXT PRIMARY KEY,
                vendor TEXT NOT NULL,
                amount REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                description TEXT NOT NULL
            )
            """
        )
        connection.commit()

def seed_sample_invoices():
    """Insert fictional invoices for development and testing."""

    sample_invoices = [
        (
            "INV-001",
            "ABC Technologies",
            35000.00,
            "pending",
            "Computer equipment"
        ),
        (
            "INV-002",
            "Global Office Supplies",
            12500.00,
            "pending",
            "Office stationery"
        ),
        (
            "INV-003",
            "Power Systems Ltd",
            75000.00,
            "pending",
            "Electrical equipment"
        ),
    ]

    with get_connection() as connection:
        connection.executemany(
            """
            INSERT OR IGNORE INTO invoices
            (invoice_id, vendor, amount, status, description)
            VALUES (?, ?, ?, ?, ?)
            """,
            sample_invoices,
        )
        connection.commit()