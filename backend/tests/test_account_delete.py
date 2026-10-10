from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import routers.authenticate as auth_router
from db.tables import Account, AccountRole, Base, Session as UserSession
from src.app import app
from db.session import get_session


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


app.dependency_overrides[get_session] = override_get_session


def setup_function():
    Base.metadata.create_all(bind=engine)


def teardown_function():
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.clear()
    app.dependency_overrides[get_session] = override_get_session


def _create_account(email: str, role: AccountRole, *, code: str = None, name: str = None):
    with TestingSessionLocal() as db:
        account = Account(
            account_email=email,
            account_code=code or email.split("@")[0],
            account_name=name or email.split("@")[0],
            role=role,
            is_active=True,
        )
        account.set_password("StrongPassword123")
        db.add(account)
        db.commit()
        db.refresh(account)
        return account.account_id


def _set_session(account_id: int, session_id: str = "session-1"):
    with TestingSessionLocal() as db:
        db.add(
            UserSession(
                session_id=session_id,
                account_id=account_id,
                expires_at=datetime.now(timezone.utc) + timedelta(days=1),
            )
        )
        db.commit()


def test_super_admin_can_delete_another_account():
    user_id = _create_account("user@example.com", AccountRole.USER, code="USER1", name="User One")
    super_id = _create_account("super@example.com", AccountRole.SUPER_ADMIN, code="SUPER1", name="Super Admin")
    _set_session(super_id, "super-session")

    client = TestClient(app)
    response = client.delete(
        f"/admin/accounts/{user_id}",
        cookies={"session_id": "super-session"},
    )

    assert response.status_code == 200
    assert response.json()["deleted_account_id"] == user_id


def test_regular_user_can_delete_their_own_account():
    user_id = _create_account("user2@example.com", AccountRole.USER, code="USER2", name="User Two")
    _set_session(user_id, "user-session")

    client = TestClient(app)
    response = client.delete(
        f"/admin/accounts/{user_id}",
        cookies={"session_id": "user-session"},
    )

    assert response.status_code == 200
    assert response.json()["deleted_account_id"] == user_id


def test_register_rejects_weak_password():
    client = TestClient(app)
    response = client.post(
        "/auth/register",
        json={
            "account_name": "Alice",
            "account_email": "alice@example.com",
            "password": "abc123",
        },
    )

    assert response.status_code == 422
    assert "Mật khẩu phải" in response.json()["detail"][0]["msg"] or "Mật khẩu phải" in response.text


def test_resend_verification_code_allows_30_seconds_between_requests():
    email = "cooldown@example.com"
    auth_router._VERIFICATION_CODES.clear()

    first_sent = datetime.now(timezone.utc)
    auth_router._VERIFICATION_CODES[email] = {
        "code": "123456",
        "sent_at": first_sent,
        "expires_at": first_sent + timedelta(minutes=5),
    }

    with pytest.raises(RuntimeError, match="30 giây"):
        auth_router._store_verification_code(email)


def test_forgot_password_flow(monkeypatch):
    user_id = _create_account("reset@example.com", AccountRole.USER, code="RESET1", name="Reset User")
    email = "reset@example.com"
    code = "123456"

    monkeypatch.setattr(auth_router, "send_verification_code", lambda target_email: {"message": "sent", "email": target_email})
    auth_router._VERIFICATION_CODES[email] = {
        "code": code,
        "sent_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=5),
    }

    client = TestClient(app)
    response = client.post("/auth/forgot-password", json={"account_email": email})
    assert response.status_code == 200

    reset_response = client.post(
        "/auth/reset-password",
        json={
            "account_email": email,
            "verification_code": code,
            "new_password": "ResetPass!2026",
        },
    )

    assert reset_response.status_code == 200
    assert reset_response.json()["message"] == "Mật khẩu đã được đặt lại thành công."

    with TestingSessionLocal() as db:
        updated = db.get(Account, user_id)
        assert updated.verify_password("ResetPass!2026") is True
