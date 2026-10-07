from fastapi import FastAPI
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

# Đọc file .env
load_dotenv()

# Lấy DATABASE_URL từ .env
DATABASE_URL = os.getenv("DATABASE_URL")

# Tạo kết nối tới PostgreSQL
engine = create_engine(DATABASE_URL)

app = FastAPI()


@app.get("/")
def home():
    return {"message": "Hello Online Judge!"}


@app.get("/create-table")
def create_table():
    with engine.connect() as connection:
        connection.execute(text("""
            CREATE TABLE test_users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(100),
                email VARCHAR(100)
            )
        """))
        connection.commit()

    return {
        "message": "Table test_users created successfully!"
    }

@app.get("/delete-table")
def delete_table():
    with engine.connect() as connection:
        connection.execute(text("DROP TABLE test_users"))
        connection.commit()

    return {
        "message": "Table test_users deleted successfully!"
    }