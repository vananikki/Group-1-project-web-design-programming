import secrets
from datetime import datetime, timedelta, timezone

from argon2.exceptions import VerificationError
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from db.schemas import LoginIn
from db.session import get_session
from db.tables import Account, Session as UserSession, ph

router = APIRouter(prefix="/auth", tags=["auth"])

# Hash giả: khi email không tồn tại vẫn tốn thời gian verify như bình thường,
# nên không ai đo thời gian phản hồi để dò email nào có trong hệ thống
DUMMY_HASH = ph.hash("dummy-password")


def authenticate(session: Session, email: str, raw_password: str) -> Account | None:
    email = email.strip().lower()
    acc = session.scalar(
        select(Account).where(Account.account_email == email)
    )

    if acc is None:
        try:
            ph.verify(DUMMY_HASH, raw_password)
        except VerificationError:
            pass
        return None

    if not acc.verify_password(raw_password):
        return None

    session.commit()  # lưu hash mới nếu verify_password đã tự rehash
    return acc


@router.post(
    "/login",
    responses={401: {"description": "Email hoặc mật khẩu không đúng"}},
)
def login_api(
    data: LoginIn,
    session: Session = Depends(get_session),
):
    # 1. Kiểm tra tài khoản + mật khẩu
    acc = authenticate(
        session,
        data.account_email,
        data.password,
    )

    if acc is None:
        raise HTTPException(
            status_code=401,
            detail="Email hoặc mật khẩu không đúng",
        )

    # 2. Tạo session ID ngẫu nhiên
    session_id = secrets.token_urlsafe(32)

    # 3. Session có hiệu lực trong 7 ngày
    expires_at = datetime.now(timezone.utc) + timedelta(days=1)

    # 4. Lưu session vào database
    user_session = UserSession(
        session_id=session_id,
        account_id=acc.account_id,
        expires_at=expires_at,
    )

    session.add(user_session)
    session.commit()

    # 5. Trả response + gửi session ID cho browser qua cookie
    response = JSONResponse(
        status_code=200,
        content={
            "message": "Đăng nhập thành công",
            "account_code": acc.account_code,
            "account_name": acc.account_name,
        },
    )

    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        secure=False,      # local HTTP; production dùng HTTPS → True
        samesite="lax",
        max_age=7 * 24 * 60 * 60,
    )

    return response