import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

load_dotenv()  # đọc file .env vào biến môi trường

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL is None:
    raise RuntimeError("Chưa đặt biến môi trường DATABASE_URL")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)


def get_session():
    with Session(engine) as session:
        yield session

