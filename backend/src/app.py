from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

from routers.login import router as auth_router
from routers.logout import router as logout_router
from routers.register import router as register_router


load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://100.73.218.40:5500,http://localhost:5500,http://127.0.0.1:5500",
    ).split(",")
    if origin.strip()
]

engine = create_engine(DATABASE_URL)

app = FastAPI()

app.include_router(auth_router)
app.include_router(logout_router)
app.include_router(register_router)


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


app = CORSMiddleware(
    app,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)