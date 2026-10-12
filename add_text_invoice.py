
from finance_app.database import get_connection

with get_connection() as connection:
    connection.execute(
        """
        INSERT OR IGNORE INTO invoices
        (invoice_id, vendor, amount, status, description)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            "INV-004",
            "Test Vendor",
            75000,
            "pending",
            "Approval threshold test",
        ),
    )
    connection.commit()

print("Test invoice created successfully.")