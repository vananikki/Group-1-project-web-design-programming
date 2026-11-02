import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from db.tables_phase1 import Session as UserSession

BACKEND_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_ROOT / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("Chưa đặt biến môi trường DATABASE_URL trong backend/.env")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)


def get_all_sessions() -> list[UserSession]:
    """Lấy toàn bộ dữ liệu trong bảng session bằng ORM, hoàn toàn tách khỏi app."""
    with Session(engine) as db:
        return db.query(UserSession).order_by(UserSession.created_at.asc()).all()


if __name__ == "__main__":
    sessions = get_all_sessions()

    if not sessions:
        print("[INFO] Bảng session hiện đang rỗng.")
    else:
        for row in sessions:
            print({
                "session_id": row.session_id,
                "account_id": row.account_id,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "expires_at": row.expires_at.isoformat() if row.expires_at else None,
            })
