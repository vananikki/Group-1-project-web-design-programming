from sqlalchemy import inspect, text

from db.session import engine


with engine.begin() as connection:
    account_columns = {
        column["name"] for column in inspect(connection).get_columns("account")
    }
    if "is_active" not in account_columns:
        connection.execute(
            text(
                "ALTER TABLE account "
                "ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE"
            )
        )

    connection.execute(
        text(
            "UPDATE account "
            "SET is_active = TRUE "
            "WHERE is_active IS NULL OR is_active = FALSE"
        )
    )

print("Account is_active column ensured and existing rows were set to active.")
