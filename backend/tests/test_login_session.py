from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from db.session import SESSION_COOKIE_SECURE, SESSION_TTL, get_session
from db.tables_phase1 import Account, AccountRole, Base, Session as UserSession
from src.app import app

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def override_get_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client():
    previous = app.dependency_overrides.get(get_session)
    app.dependency_overrides[get_session] = override_get_session
    Base.metadata.create_all(bind=engine)
    try:
        yield TestClient(app)
    finally:
        Base.metadata.drop_all(bind=engine)
        if previous is None:
            app.dependency_overrides.pop(get_session, None)
        else:
            app.dependency_overrides[get_session] = previous


def create_active_account():
    with TestingSessionLocal() as db:
        account = Account(
            account_email="login@example.com",
            account_code="LOGIN1",
            account_name="Login User",
            role=AccountRole.USER,
            is_active=True,
        )
        account.set_password("StrongPassword123")
        db.add(account)
        db.commit()
        db.refresh(account)
        return account.account_id


def test_login_sets_http_only_cookie_with_matching_session_expiry(client):
    account_id = create_active_account()

    response = client.post(
        "/auth/login",
        json={
            "account_email": "login@example.com",
            "password": "StrongPassword123",
        },
    )

    assert response.status_code == 200, response.text
    cookie = response.headers["set-cookie"].lower()
    assert "session_id=" in cookie
    assert "httponly" in cookie
    assert "samesite=lax" in cookie
    assert f"max-age={int(SESSION_TTL.total_seconds())}" in cookie
    assert ("secure" in cookie) is SESSION_COOKIE_SECURE

    with TestingSessionLocal() as db:
        user_session = db.query(UserSession).one()
        assert user_session.account_id == account_id
        assert datetime.now(timezone.utc) < user_session.expires_at.replace(
            tzinfo=timezone.utc
        ) <= datetime.now(timezone.utc) + SESSION_TTL + timedelta(seconds=1)

    me_response = client.get("/auth/me")
    assert me_response.status_code == 200, me_response.text
    assert me_response.json()["account_id"] == account_id

    logout_response = client.post("/auth/logout")
    assert logout_response.status_code == 200
    assert "max-age=0" in logout_response.headers["set-cookie"].lower()
    assert client.get("/auth/me").status_code == 401


def test_login_rejects_invalid_password_without_setting_session_cookie(client):
    create_active_account()

    response = client.post(
        "/auth/login",
        json={
            "account_email": "login@example.com",
            "password": "WrongPassword123",
        },
    )

    assert response.status_code == 401
    assert "set-cookie" not in response.headers
    assert client.get("/auth/me").status_code == 401
