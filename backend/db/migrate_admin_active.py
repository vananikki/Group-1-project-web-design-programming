from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from db.session import engine
from db.tables import Account, AccountRole, Admin


with engine.begin() as connection:
    admin_columns = {
        column["name"] for column in inspect(connection).get_columns("admin")
    }
    if "is_active" not in admin_columns:
        connection.execute(
            text(
                "ALTER TABLE admin "
                "ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE"
            )
        )

with Session(engine) as session:
    accounts = session.query(Account).all()
    admins_by_account_id = {
        admin.account_id: admin for admin in session.query(Admin).all()
    }

    for account in accounts:
        should_be_admin = account.role in {
            AccountRole.ADMIN,
            AccountRole.SUPER_ADMIN,
        }
        admin = admins_by_account_id.get(account.account_id)

        if should_be_admin and admin is None:
            admin = Admin(account_id=account.account_id, is_active=True)
            session.add(admin)
        elif admin is not None:
            admin.is_active = should_be_admin

    session.commit()

print("Admin records synchronized with account roles.")
