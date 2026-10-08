from session import engine
from tables import Account, AccountRole, ph
from sqlalchemy.orm import Session


email = "admin@example.com"
name = "Super Admin"
password = "12345678"

with Session(engine) as session:
    account = Account(
        account_email=email,
        account_code="admin",
        account_name=name,
        password_hash=ph.hash(password),
        role=AccountRole.SUPER_ADMIN,
    )

    session.add(account)
    session.commit()

    print("Đã tạo tài khoản SUPER_ADMIN.")
    print(f"Email: {email}")
    print(f"Password: {password}")