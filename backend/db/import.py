from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from tables import Account


class AccountExistsError(Exception):
    """Tên hoặc email đã được dùng."""


def create_account(
    session: Session,
    name: str,
    email: str,
    raw_password: str,
) -> Account:
    name = name.strip()
    email = email.strip().lower()

    existed = session.scalar(
        select(Account).where(
            (Account.account_email == email) | (Account.account_name == name)
        )
    )
    if existed is not None:
        raise AccountExistsError("Tên hoặc email đã tồn tại")

    acc = Account(account_name=name, account_email=email)
    acc.set_password(raw_password)

    session.add(acc)
    try:
        session.commit()
    except IntegrityError:
        # Trường hợp hai request đăng ký cùng lúc vượt qua bước kiểm tra trên
        session.rollback()
        raise AccountExistsError("Tên hoặc email đã tồn tại")

    session.refresh(acc)  # nạp account_seq, account_code, created_at do DB sinh
    return acc