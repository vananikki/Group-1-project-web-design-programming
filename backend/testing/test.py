
import os
import base64
from pathlib import Path

from dotenv import load_dotenv
from google.auth.exceptions import RefreshError
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from email.mime.text import MIMEText


BACKEND_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_ROOT / ".env")

CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH")
TOKEN_PATH = os.getenv("GOOGLE_TOKEN_PATH", "token.json")

if not CREDENTIALS_PATH:
    raise RuntimeError("Chưa cấu hình GOOGLE_CREDENTIALS_PATH")

if not os.path.exists(CREDENTIALS_PATH):
    raise FileNotFoundError(
        f"Không tìm thấy credentials.json: {CREDENTIALS_PATH}"
    )

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send"
]


# =========================
# 1. Xác thực Google
# =========================

credentials = None

# Đọc token đã lưu nếu tồn tại
if os.path.exists(TOKEN_PATH):
    credentials = Credentials.from_authorized_user_file(
        TOKEN_PATH,
        SCOPES,
    )

# Token hết hạn thì tự làm mới; nếu refresh token đã invalid/expired thì bắt đầu lại OAuth
if credentials and credentials.expired and credentials.refresh_token:
    try:
        credentials.refresh(Request())
    except RefreshError:
        credentials = None
        if os.path.exists(TOKEN_PATH):
            os.remove(TOKEN_PATH)

# Chỉ yêu cầu chọn tài khoản nếu chưa có credentials hợp lệ
if not credentials or not credentials.valid:
    flow = InstalledAppFlow.from_client_secrets_file(
        CREDENTIALS_PATH,
        SCOPES,
    )

    credentials = flow.run_local_server(port=0)

# Lưu token để dùng cho những lần chạy sau
with open(TOKEN_PATH, "w", encoding="utf-8") as f:
    f.write(credentials.to_json())

print("Xác thực Google thành công!")


# =========================
# 2. Tạo Gmail API service
# =========================

service = build(
    "gmail",
    "v1",
    credentials=credentials,
)


# =========================
# 3. Hàm gửi email
# =========================

def send_email(to_email: str, subject: str, body: str):
    message = MIMEText(body, "plain", "utf-8")

    message["to"] = to_email
    message["subject"] = subject

    raw_message = base64.urlsafe_b64encode(
        message.as_bytes()
    ).decode("utf-8")

    result = service.users().messages().send(
        userId="me",
        body={"raw": raw_message},
    ).execute()

    print("Gửi email thành công!")
    print("Message ID:", result["id"])

    return result


# =========================
# 4. Test gửi email
# =========================

if __name__ == "__main__":
    try:
        send_email(
            to_email="ngaodu18072006@gmail.com",
            subject="Email Tự động từ Online Judge0",
            body="""
Xin chào!

Đây là email được gửi tự động
bằng Gmail API từ Python.

Online Judge test.
""",
        )

    except HttpError as e:
        print("Lỗi Gmail API:", e)
