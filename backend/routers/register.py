from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from db.schemas import RegisterIn
from db.session import get_session
from db.tables import Account, AccountRole


router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)


class AccountExistsError(Exception):
    """Email đã được sử dụng."""


def create_account(
    session: Session,
    name: str,
    email: str,
    raw_password: str,
) -> Account:

    name = name.strip()
    email = email.strip().lower()

    # Kiểm tra email đã tồn tại chưa
    existed = session.scalar(
        select(Account).where(
            Account.account_email == email
        )
    )

    if existed is not None:
        raise AccountExistsError(
            "Email đã được sử dụng"
        )

    # Tạo Account
    acc = Account(
        account_name=name,
        account_email=email,
        role=AccountRole.USER,
        password_hash="",  # tạm thời, sẽ được set bên dưới
    )

    acc.set_password(raw_password)

    session.add(acc)

    try:
        # Cho DB sinh account_id trước
        session.flush()

        # Sinh account_code từ account_id
        acc.account_code = f"ACC{acc.account_id:06d}"

        session.commit()

    except IntegrityError:
        session.rollback()
        raise AccountExistsError(
            "Email đã được sử dụng"
        )

    # Nạp lại dữ liệu từ DB
    session.refresh(acc)

    return acc


@router.post(
    "/register",
    status_code=201,
    responses={
        409: {
            "description": "Email đã được sử dụng"
        }
    },
)
def register_api(
    data: RegisterIn,
    session: Session = Depends(get_session),
):
    try:
        acc = create_account(
            session,
            data.account_name,
            data.account_email,
            data.password,
        )

    except AccountExistsError as e:
        raise HTTPException(
            status_code=409,
            detail=str(e),
        )

    return JSONResponse(
        status_code=201,
        content={
            "message": "Đăng ký thành công",
            "account_code": acc.account_code,
            "account_name": acc.account_name,
        },
    )