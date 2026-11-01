from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import routers.authenticate as auth_router
from db.tables_phase1 import Account, AccountRole, Base, Session as UserSession
from db.tables_phase2 import Contest, Language, Problem, Submission
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




@pytest.fixture(autouse=True)
def _override_db_session():
    previous = app.dependency_overrides.get(get_session)
    app.dependency_overrides[get_session] = override_get_session
    Base.metadata.create_all(bind=engine)
    try:
        yield
    finally:
        Base.metadata.drop_all(bind=engine)
        if previous is None:
            app.dependency_overrides.pop(get_session, None)
        else:
            app.dependency_overrides[get_session] = previous


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


def test_super_admin_cannot_delete_their_own_account():
    super_id = _create_account(
        "super-self-delete@example.com",
        AccountRole.SUPER_ADMIN,
        code="SUPERSELF",
        name="Super Admin",
    )
    _set_session(super_id, "super-self-session")

    response = TestClient(app).delete(
        f"/admin/accounts/{super_id}",
        cookies={"session_id": "super-self-session"},
    )

    assert response.status_code == 403
    with TestingSessionLocal() as db:
        assert db.get(Account, super_id) is not None


def test_regular_user_cannot_delete_their_own_account():
    user_id = _create_account("user2@example.com", AccountRole.USER, code="USER2", name="User Two")
    _set_session(user_id, "user-session")

    client = TestClient(app)
    response = client.delete(
        f"/admin/accounts/{user_id}",
        cookies={"session_id": "user-session"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Không thể tự xóa tài khoản của mình"
    with TestingSessionLocal() as db:
        assert db.get(Account, user_id) is not None


def test_admin_cannot_delete_their_own_account():
    admin_id = _create_account(
        "admin-self-delete@example.com",
        AccountRole.ADMIN,
        code="ADMINSELF",
        name="Admin",
    )
    _set_session(admin_id, "admin-self-session")

    response = TestClient(app).delete(
        f"/admin/accounts/{admin_id}",
        cookies={"session_id": "admin-self-session"},
    )

    assert response.status_code == 403
    with TestingSessionLocal() as db:
        assert db.get(Account, admin_id) is not None


def test_delete_anonymizes_and_preserves_related_judge_data():
    user_id = _create_account(
        "author@example.com",
        AccountRole.USER,
        code="AUTHOR1",
        name="Problem Author",
    )
    super_id = _create_account(
        "author-delete-super@example.com",
        AccountRole.SUPER_ADMIN,
        code="AUTHSUPER",
        name="Super Admin",
    )
    _set_session(super_id, "author-delete-super-session")

    with TestingSessionLocal() as db:
        language = Language(name="Python")
        problem = Problem(
            problem_name="Preserved problem",
            time_limit=1,
            memory_limit=128,
            created_by=user_id,
        )
        contest = Contest(
            contest_name="Preserved contest",
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc) + timedelta(hours=1),
            created_by=user_id,
        )
        db.add_all([language, problem, contest])
        db.flush()
        submission = Submission(
            problem_id=problem.problem_id,
            account_id=user_id,
            contest_id=contest.contest_id,
            language_id=language.language_id,
            status="Accepted",
        )
        db.add(submission)
        db.commit()
        problem_id = problem.problem_id
        contest_id = contest.contest_id
        submission_id = submission.submission_id

    response = TestClient(app).delete(
        f"/admin/accounts/{user_id}",
        cookies={"session_id": "author-delete-super-session"},
    )

    assert response.status_code == 200
    with TestingSessionLocal() as db:
        assert db.get(Account, user_id) is None
        assert db.get(Problem, problem_id).created_by is None
        assert db.get(Contest, contest_id).created_by is None
        assert db.get(Submission, submission_id).account_id is None


def test_delete_preflight_allows_configured_frontend_origin():
    origin = "http://100.73.218.40:5500"
    response = TestClient(app).options(
        "/admin/accounts/1",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "DELETE",
            "Access-Control-Request-Private-Network": "true",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
    assert "DELETE" in response.headers["access-control-allow-methods"]
    assert response.headers["access-control-allow-private-network"] == "true"


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


def test_verification_email_rate_limits_per_address_and_globally():
    email = "cooldown@example.com"
    now = [100.0]
    limiter = auth_router._EmailRateLimiter(clock=lambda: now[0])
    limiter.reserve(email)
    limiter.mark_sent(email)

    now[0] += 179
    with pytest.raises(RuntimeError, match="3 phút"):
        limiter.reserve(email)

    now[0] += 1
    limiter.reserve(email)
    limiter.release(email)

    global_limiter = auth_router._EmailRateLimiter(clock=lambda: now[0])
    for index in range(auth_router.EMAIL_SEND_LIMIT):
        target = f"user{index}@example.com"
        global_limiter.reserve(target)
        global_limiter.mark_sent(target)

    assert global_limiter.wait_for_global_slot() == 60
    now[0] += 60
    assert global_limiter.wait_for_global_slot() == 0


def test_verification_code_expires_after_two_minutes():
    email = "expiry@example.com"
    code = auth_router._store_verification_code(email, "123456")
    payload = auth_router._VERIFICATION_CODES[email]

    assert code == "123456"
    assert (
        payload["expires_at"] - payload["sent_at"]
    ).total_seconds() == auth_router.OTP_TTL_SECONDS == 120


def test_send_code_endpoint_queues_email(monkeypatch):
    queued_emails = []
    monkeypatch.setattr(
        auth_router._VERIFICATION_EMAIL_QUEUE,
        "enqueue",
        queued_emails.append,
    )

    response = TestClient(app).post(
        "/auth/send-code",
        json={"account_email": "queue@example.com"},
    )

    assert response.status_code == 202
    assert queued_emails == ["queue@example.com"]


def test_forgot_password_flow(monkeypatch):
    user_id = _create_account("reset@example.com", AccountRole.USER, code="RESET1", name="Reset User")
    email = "reset@example.com"
    code = "123456"

    monkeypatch.setattr(auth_router, "send_verification_code", lambda target_email: {"message": "sent", "email": target_email})
    auth_router._VERIFICATION_CODES[email] = {
        "code": code,
        "sent_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=2),
    }

    client = TestClient(app)
    response = client.post("/auth/forgot-password", json={"account_email": email})
    assert response.status_code == 202

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
