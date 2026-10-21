import base64
import logging
import os
import secrets
import threading
import time
from collections import deque
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from pathlib import Path

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
from db.tables_phase1 import Account


BACKEND_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_ROOT / ".env")

router = APIRouter(prefix="/auth", tags=["auth"])

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
GOOGLE_CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH")
GOOGLE_TOKEN_PATH = os.getenv(
    "GOOGLE_TOKEN_PATH",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "token.json")),
)

OTP_TTL_SECONDS = 2 * 60
OTP_RESEND_SECONDS = 3 * 60
EMAIL_SEND_LIMIT = 5
EMAIL_SEND_WINDOW_SECONDS = 60
_VERIFICATION_CODES: dict[str, dict[str, str | datetime]] = {}
_GMAIL_SERVICE = None
_LOGGER = logging.getLogger(__name__)


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


class _EmailRateLimiter:
    def __init__(self, clock=time.monotonic):
        self._clock = clock
        self._sent_times: deque[float] = deque()
        self._last_sent_by_email: dict[str, float] = {}
        self._pending_emails: set[str] = set()
        self._lock = threading.Lock()

    def reserve(self, email: str) -> None:
        now = self._clock()
        with self._lock:
            expired_emails = [
                address
                for address, sent_at in self._last_sent_by_email.items()
                if now - sent_at >= OTP_RESEND_SECONDS
            ]
            for address in expired_emails:
                self._last_sent_by_email.pop(address, None)

            last_sent = self._last_sent_by_email.get(email)
            if email in self._pending_emails:
                raise RuntimeError("Email xác thực đang chờ gửi. Vui lòng đợi.")
            if last_sent is not None:
                remaining = OTP_RESEND_SECONDS - (now - last_sent)
                if remaining > 0:
                    raise RuntimeError(
                        "Vui lòng chờ 3 phút giữa các lần gửi email đến cùng địa chỉ."
                    )
                self._last_sent_by_email.pop(email, None)
            self._pending_emails.add(email)

    def wait_for_global_slot(self) -> float:
        now = self._clock()
        with self._lock:
            while (
                self._sent_times
                and now - self._sent_times[0] >= EMAIL_SEND_WINDOW_SECONDS
            ):
                self._sent_times.popleft()
            if len(self._sent_times) < EMAIL_SEND_LIMIT:
                return 0
            return max(
                0,
                self._sent_times[0] + EMAIL_SEND_WINDOW_SECONDS - now,
            )

    def mark_sent(self, email: str) -> None:
        now = self._clock()
        with self._lock:
            self._sent_times.append(now)
            self._last_sent_by_email[email] = now
            self._pending_emails.discard(email)

    def release(self, email: str) -> None:
        with self._lock:
            self._pending_emails.discard(email)


class _VerificationEmailQueue:
    def __init__(self):
        self._emails: deque[str] = deque()
        self._condition = threading.Condition()
        self._rate_limiter = _EmailRateLimiter()
        self._worker: threading.Thread | None = None

    def enqueue(self, email: str) -> None:
        with self._condition:
            self._rate_limiter.reserve(email)
            self._emails.append(email)
            if self._worker is None or not self._worker.is_alive():
                self._worker = threading.Thread(
                    target=self._run,
                    name="verification-email-queue",
                    daemon=True,
                )
                try:
                    self._worker.start()
                except RuntimeError:
                    self._emails.pop()
                    self._rate_limiter.release(email)
                    raise
            self._condition.notify()

    def _run(self) -> None:
        while True:
            with self._condition:
                while not self._emails:
                    self._condition.wait()
                wait_seconds = self._rate_limiter.wait_for_global_slot()
                if wait_seconds > 0:
                    self._condition.wait(timeout=wait_seconds)
                    continue
                email = self._emails.popleft()

            code = _generate_verification_code()
            try:
                _deliver_verification_code(email, code)
                self._rate_limiter.mark_sent(email)
                _store_verification_code(email, code)
            except Exception:
                _LOGGER.exception("Could not deliver a queued verification email")
                self._rate_limiter.release(email)
                continue


_VERIFICATION_EMAIL_QUEUE = _VerificationEmailQueue()


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


def _store_verification_code(email: str, code: str | None = None) -> str:
    normalized_email = _normalize_email(email)
    now = datetime.now(timezone.utc)
    _clean_expired_codes()
    code = code or _generate_verification_code()

    _VERIFICATION_CODES[normalized_email] = {
        "code": code,
        "sent_at": now,
        "expires_at": now + timedelta(seconds=OTP_TTL_SECONDS),
    }
    return code


def _deliver_verification_code(email: str, code: str) -> None:
    subject = "Mã xác thực email - Online Judge"
    body = (
        "Xin chào!\n\n"
        f"Mã xác thực email của bạn là: {code}\n"
        "Mã này có hiệu lực trong 2 phút.\n\n"
        "Nếu bạn không yêu cầu mã này, hãy bỏ qua email này."
    )
    try:
        send_email(email, subject, body)
    except HttpError as exc:  # pragma: no cover - depends on Gmail API
        raise RuntimeError("Không thể gửi mã xác thực qua Gmail") from exc


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

    _VERIFICATION_EMAIL_QUEUE.enqueue(normalized_email)

    return {
        "message": "Yêu cầu gửi mã xác thực đã được đưa vào hàng đợi.",
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


@router.post("/send-code", status_code=202)
@router.post("/send-otp", status_code=202)
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


@router.post("/forgot-password", status_code=202)
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
