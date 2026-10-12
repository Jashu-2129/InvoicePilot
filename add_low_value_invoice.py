
from finance_app.database import get_connection

with get_connection() as connection:
    connection.execute(
        """
        INSERT OR IGNORE INTO invoices
        (invoice_id, vendor, amount, status, description)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            "INV-005",
            "Low Value Test Vendor",
            12000,
            "pending",
            "Low-value approval test",
        ),
    )
    connection.commit()

print("Test invoice INV-005 created if it did not already exist.")