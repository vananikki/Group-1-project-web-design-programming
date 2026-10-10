import base64
import os
import secrets
from pathlib import Path
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from db.schemas import validate_password_strength
from db.session import get_session
from db.tables import Account


BACKEND_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_ROOT / ".env")

router = APIRouter(prefix="/auth", tags=["auth"])

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
GOOGLE_CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH")
GOOGLE_TOKEN_PATH = os.getenv(
    "GOOGLE_TOKEN_PATH",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "token.json")),
)

OTP_TTL_SECONDS = 5 * 60
OTP_RESEND_SECONDS = 30
_VERIFICATION_CODES: dict[str, dict[str, str | datetime]] = {}
_GMAIL_SERVICE = None


class EmailRequest(BaseModel):
    account_email: EmailStr


class VerifyCodeRequest(BaseModel):
    account_email: EmailStr
    verification_code: str = Field(min_length=6, max_length=6)


class ForgotPasswordRequest(BaseModel):
    account_email: EmailStr


class ResetPasswordRequest(BaseModel):
    account_email: EmailStr
    verification_code: str = Field(min_length=6, max_length=6)
    new_password: str = Field(max_length=128)


def _build_gmail_service():
    global _GMAIL_SERVICE

    if _GMAIL_SERVICE is not None:
        return _GMAIL_SERVICE

    if not GOOGLE_CREDENTIALS_PATH:
        raise RuntimeError("Chưa cấu hình GOOGLE_CREDENTIALS_PATH")

    if not os.path.exists(GOOGLE_CREDENTIALS_PATH):
        raise FileNotFoundError(
            f"Không tìm thấy credentials.json: {GOOGLE_CREDENTIALS_PATH}"
        )

    credentials: Credentials | None = None

    if os.path.exists(GOOGLE_TOKEN_PATH):
        try:
            credentials = Credentials.from_authorized_user_file(
                GOOGLE_TOKEN_PATH,
                SCOPES,
            )
            if credentials and credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
        except RefreshError:
            credentials = None
            if os.path.exists(GOOGLE_TOKEN_PATH):
                os.remove(GOOGLE_TOKEN_PATH)

    if not credentials or not credentials.valid:
        flow = InstalledAppFlow.from_client_secrets_file(
            GOOGLE_CREDENTIALS_PATH,
            SCOPES,
        )
        credentials = flow.run_local_server(port=0)

    with open(GOOGLE_TOKEN_PATH, "w", encoding="utf-8") as token_file:
        token_file.write(credentials.to_json())

    _GMAIL_SERVICE = build("gmail", "v1", credentials=credentials)
    return _GMAIL_SERVICE


def send_email(to_email: str, subject: str, body: str):
    service = _build_gmail_service()
    message = MIMEText(body, "plain", "utf-8")
    message["to"] = to_email
    message["subject"] = subject

    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

    result = service.users().messages().send(
        userId="me",
        body={"raw": raw_message},
    ).execute()

    return result


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _generate_verification_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _clean_expired_codes() -> None:
    now = datetime.now(timezone.utc)
    expired_emails = [
        email
        for email, payload in _VERIFICATION_CODES.items()
        if datetime.fromisoformat(str(payload["expires_at"])) <= now
    ]
    for email in expired_emails:
        _VERIFICATION_CODES.pop(email, None)


def _store_verification_code(email: str) -> str:
    normalized_email = _normalize_email(email)
    now = datetime.now(timezone.utc)
    code = _generate_verification_code()
    _clean_expired_codes()

    payload = _VERIFICATION_CODES.get(normalized_email)
    if payload is not None:
        last_sent = datetime.fromisoformat(str(payload["sent_at"]))
        if (now - last_sent).total_seconds() < OTP_RESEND_SECONDS:
            raise RuntimeError("Vui lòng chờ 30 giây trước khi gửi lại mã xác thực.")

    _VERIFICATION_CODES[normalized_email] = {
        "code": code,
        "sent_at": now,
        "expires_at": now + timedelta(seconds=OTP_TTL_SECONDS),
    }
    return code


def _validate_verification_code(email: str, submitted_code: str) -> bool:
    normalized_email = _normalize_email(email)
    _clean_expired_codes()
    payload = _VERIFICATION_CODES.get(normalized_email)
    if payload is None:
        return False

    if datetime.fromisoformat(str(payload["expires_at"])) <= datetime.now(timezone.utc):
        _VERIFICATION_CODES.pop(normalized_email, None)
        return False

    is_valid = str(payload["code"]) == submitted_code.strip()
    if is_valid:
        _VERIFICATION_CODES.pop(normalized_email, None)
    return is_valid


def send_verification_code(email: str) -> dict:
    normalized_email = _normalize_email(email)
    if not normalized_email or "@" not in normalized_email:
        raise ValueError("Email không hợp lệ")

    code = _store_verification_code(normalized_email)
    subject = "Mã xác thực email - Online Judge"
    body = (
        "Xin chào!\n\n"
        f"Mã xác thực email của bạn là: {code}\n"
        "Mã này có hiệu lực trong 5 phút.\n\n"
        "Nếu bạn không yêu cầu mã này, hãy bỏ qua email này."
    )

    try:
        send_email(normalized_email, subject, body)
    except HttpError as exc:  # pragma: no cover - depends on Gmail API
        raise RuntimeError("Không thể gửi mã xác thực qua Gmail") from exc

    return {
        "message": "Mã xác thực đã được gửi đến email của bạn.",
        "email": normalized_email,
    }


def verify_verification_code(email: str, submitted_code: str) -> bool:
    return _validate_verification_code(email, submitted_code)


def activate_account_from_email(email: str, session: Session) -> bool:
    normalized_email = _normalize_email(email)
    account = session.scalar(
        select(Account).where(Account.account_email == normalized_email)
    )
    if account is None:
        return False

    if account.is_active:
        return True

    account.is_active = True
    session.commit()
    return True


@router.post("/send-code")
@router.post("/send-otp")
def send_code_api(
    data: EmailRequest,
    session: Session = Depends(get_session),
):
    email = _normalize_email(data.account_email)
    existed = session.scalar(
        select(Account).where(Account.account_email == email)
    )

    if existed is not None and existed.is_active:
        raise HTTPException(
            status_code=409,
            detail="Email đã được sử dụng để đăng ký.",
        )

    try:
        result = send_verification_code(email)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc

    return result


@router.post("/verify-code")
@router.post("/verify-otp")
def verify_code_api(
    data: VerifyCodeRequest,
    session: Session = Depends(get_session),
):
    if not verify_verification_code(data.account_email, data.verification_code):
        raise HTTPException(
            status_code=400,
            detail="Mã xác thực không đúng hoặc đã hết hạn.",
        )

    activated = activate_account_from_email(data.account_email, session)

    return {
        "message": "Email đã được xác thực thành công.",
        "account_email": _normalize_email(data.account_email),
        "account_activated": activated,
    }


@router.post("/forgot-password")
def forgot_password_api(
    data: ForgotPasswordRequest,
    session: Session = Depends(get_session),
):
    email = _normalize_email(data.account_email)
    account = session.scalar(select(Account).where(Account.account_email == email))
    if account is None:
        raise HTTPException(
            status_code=404,
            detail="Email chưa được đăng ký trong hệ thống.",
        )

    try:
        result = send_verification_code(email)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc

    return {
        "message": "Mã xác thực đặt lại mật khẩu đã được gửi đến email của bạn.",
        **result,
    }


@router.post("/reset-password")
def reset_password_api(
    data: ResetPasswordRequest,
    session: Session = Depends(get_session),
):
    email = _normalize_email(data.account_email)
    account = session.scalar(select(Account).where(Account.account_email == email))
    if account is None:
        raise HTTPException(
            status_code=404,
            detail="Email chưa được đăng ký trong hệ thống.",
        )

    if not verify_verification_code(email, data.verification_code):
        raise HTTPException(
            status_code=400,
            detail="Mã xác thực không đúng hoặc đã hết hạn.",
        )

    try:
        validate_password_strength(data.new_password)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    account.set_password(data.new_password)
    session.commit()

    return {
        "message": "Mật khẩu đã được đặt lại thành công.",
        "account_email": email,
    }


# Backward-compatible aliases for the project naming style.
send_one_time_code = send_verification_code
verify_one_time_code = verify_verification_code
