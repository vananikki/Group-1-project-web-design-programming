import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine

from routers.authenticate import router as authenticate_router
from routers.login import router as login_router
from routers.logout import router as logout_router
from routers.manage_accounts import router as manage_accounts_router
from routers.register import router as register_router

BACKEND_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_ROOT / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)


def get_allowed_origins() -> list[str]:
    configured = os.getenv("CORS_ORIGINS", "")
    default_origins = [
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://0.0.0.0:5500",
        "http://100.73.218.40:5500",
        "http://172.17.22.24:5500",
        "http://172.17.0.0:5500",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://100.73.218.40:8000",
    ]
    origins = [origin.strip() for origin in configured.split(",") if origin.strip()]
    return list(dict.fromkeys(default_origins + origins))


app = FastAPI(title="Online Judge")

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|0\.0\.0\.0|100\.73\.218\.40|172\.17\..+)(?::\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_private_network=True,
)

app.include_router(authenticate_router)
app.include_router(login_router)
app.include_router(logout_router)
app.include_router(register_router)
app.include_router(manage_accounts_router)


@app.get("/")
def home():
    return {"message": "Hello Online Judge!"}
