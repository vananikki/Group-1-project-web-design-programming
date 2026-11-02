import os
from pathlib import Path
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from sqlalchemy import Engine, create_engine, delete
from sqlalchemy.orm import Session

from db.tables_phase1 import Session as UserSession

BACKEND_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_ROOT / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL is None:
    raise RuntimeError("Chưa đặt biến môi trường DATABASE_URL")

SESSION_TTL = timedelta(days=1)
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)


def cleanup_expired_sessions(db_engine: Engine | None = None) -> int:
    """Delete stale session rows using ORM delete, not string concatenation."""
    target_engine = db_engine or engine
    now_utc = datetime.now(timezone.utc)
    with Session(target_engine) as session:
        result = session.execute(
            delete(UserSession).where(UserSession.expires_at <= now_utc)
        )
        session.commit()
        return int(result.rowcount or 0)


def get_session():
    with Session(engine) as session:
        yield session
