import secrets

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from db.schemas import RegisterIn, validate_password_strength
from db.session import get_session
from db.tables import Account, AccountRole
from routers.authenticate import send_verification_code


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

    if len(name) < 3:
        raise HTTPException(
            status_code=422,
            detail="Tên tài khoản phải có ít nhất 3 ký tự",
        )

    try:
        validate_password_strength(raw_password)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

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
        is_active=False,
        role=AccountRole.USER,
        account_code=f"PENDING{secrets.token_hex(6)}",
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
        if session.scalar(
            select(Account).where(Account.account_email == email)
        ) is not None:
            raise AccountExistsError("Email đã được sử dụng")
        raise

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

    try:
        send_verification_code(acc.account_email)
        verification_message = "Tài khoản đã được tạo. Vui lòng xác thực email để kích hoạt tài khoản."
    except Exception:
        verification_message = (
            "Tài khoản đã được tạo nhưng không thể gửi mã xác thực ngay lúc này. "
            "Bạn có thể gửi lại mã ở màn hình xác thực email."
        )

    return JSONResponse(
        status_code=201,
        content={
            "message": verification_message,
            "account_code": acc.account_code,
            "account_name": acc.account_name,
            "is_active": acc.is_active,
        },
    )