from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import routers.judge_admin as judge_admin
from db.tables_phase1 import (
    Account,
    AccountRole,
    Admin,
    Base,
    ClassJoinRequest,
    ManageClass,
    Session as UserSession,
)
from db.tables_phase2 import Language, Submission, Testcase as JudgeTestcase
from db.session import get_session
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


def test_admin_can_create_problem_and_class():
    admin_id = _create_account("admin@example.com", AccountRole.ADMIN, code="ADM1", name="Admin")
    _set_session(admin_id, "admin-session")

    client = TestClient(app)

    response = client.post(
        "/admin/judge/problems",
        json={
            "problem_name": "Sum of Two Numbers",
            "description": "Compute a + b",
            "input_description": "Two integers",
            "output_description": "One integer",
            "time_limit": 1,
            "memory_limit": 256,
            "access_modifier": "public",
        },
        cookies={"session_id": "admin-session"},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["problem_name"] == "Sum of Two Numbers"
    assert payload["access_modifier"] == "public"

    class_response = client.post(
        "/admin/judge/academic-classes",
        json={"class_name": "CS101 Basic Programming"},
        cookies={"session_id": "admin-session"},
    )

    assert class_response.status_code == 200, class_response.text
    class_payload = class_response.json()
    assert class_payload["class_name"] == "CS101 Basic Programming"


def test_admin_can_attach_public_problem_to_contest():
    admin_id = _create_account("contest-admin@example.com", AccountRole.ADMIN, code="ADM2", name="Contest Admin")
    _set_session(admin_id, "contest-session")

    client = TestClient(app)
    problem_response = client.post(
        "/admin/judge/problems",
        json={
            "problem_name": "Prime Check",
            "description": "Return yes/no",
            "input_description": "Integer",
            "output_description": "Result",
            "time_limit": 2,
            "memory_limit": 512,
            "access_modifier": "public",
        },
        cookies={"session_id": "contest-session"},
    )
    problem_id = problem_response.json()["problem_id"]

    contest_response = client.post(
        "/admin/judge/contests",
        json={
            "contest_name": "Week 1 Contest",
            "description": "Warm up contest",
            "start_time": "2026-10-01T10:00:00Z",
            "end_time": "2026-10-01T12:00:00Z",
        },
        cookies={"session_id": "contest-session"},
    )
    contest_id = contest_response.json()["contest_id"]

    attach_response = client.post(
        f"/admin/judge/contests/{contest_id}/problems",
        json={"problem_id": problem_id, "problem_order": 1},
        cookies={"session_id": "contest-session"},
    )

    assert attach_response.status_code == 200, attach_response.text
    assert attach_response.json()["problem_id"] == problem_id

    detail_response = client.get(
        f"/admin/judge/contests/{contest_id}",
        cookies={"session_id": "contest-session"},
    )
    assert detail_response.status_code == 200, detail_response.text
    assert detail_response.json()["status"] == "finished"
    assert detail_response.json()["is_out_of_contest"] is True


def test_problem_testcases_can_be_created_and_replaced():
    admin_id = _create_account("testcases@example.com", AccountRole.ADMIN)
    _set_session(admin_id, "testcase-session")
    client = TestClient(app)

    response = client.post(
        "/admin/judge/problems",
        json={
            "problem_name": "Test case problem",
            "time_limit": 1,
            "memory_limit": 256,
            "testcases": [
                {"input_data": "2 3\n", "expected_output": "5\n", "point": 40},
                {"input_data": "5 7\n", "expected_output": "12\n", "point": 60},
            ],
        },
        cookies={"session_id": "testcase-session"},
    )
    assert response.status_code == 200, response.text
    problem_id = response.json()["problem_id"]

    with TestingSessionLocal() as db:
        testcases = db.scalars(
            select(JudgeTestcase).where(JudgeTestcase.problem_id == problem_id)
        ).all()
        assert [(testcase.input_data, testcase.expected_output, testcase.point) for testcase in testcases] == [
            ("2 3\n", "5\n", 40),
            ("5 7\n", "12\n", 60),
        ]

    update_response = client.patch(
        f"/admin/judge/problems/{problem_id}",
        json={
            "testcases": [
                {"input_data": "8 9\n", "expected_output": "17\n", "point": 100}
            ]
        },
        cookies={"session_id": "testcase-session"},
    )
    assert update_response.status_code == 200, update_response.text

    with TestingSessionLocal() as db:
        testcases = db.scalars(
            select(JudgeTestcase).where(JudgeTestcase.problem_id == problem_id)
        ).all()
        assert [(testcase.input_data, testcase.expected_output, testcase.point) for testcase in testcases] == [
            ("8 9\n", "17\n", 100)
        ]


def test_admin_can_manage_class_students_without_schema_changes():
    admin_id = _create_account("class-admin@example.com", AccountRole.ADMIN)
    student_account_id = _create_account("class-student@example.com", AccountRole.USER)
    _set_session(admin_id, "class-session")
    client = TestClient(app)

    class_response = client.post(
        "/admin/judge/academic-classes",
        json={"class_name": "CS 101"},
        cookies={"session_id": "class-session"},
    )
    assert class_response.status_code == 200, class_response.text
    class_id = class_response.json()["class_id"]

    add_response = client.post(
        f"/admin/judge/academic-classes/{class_id}/students",
        json={"account_id": student_account_id},
        cookies={"session_id": "class-session"},
    )
    assert add_response.status_code == 200, add_response.text

    detail_response = client.get(
        f"/admin/judge/academic-classes/{class_id}",
        cookies={"session_id": "class-session"},
    )
    assert detail_response.status_code == 200, detail_response.text
    assert detail_response.json()["students"][0]["account_id"] == student_account_id

    remove_response = client.delete(
        f"/admin/judge/academic-classes/{class_id}/students/{student_account_id}",
        cookies={"session_id": "class-session"},
    )
    assert remove_response.status_code == 200, remove_response.text


def test_students_request_class_access_and_owner_approves():
    owner_id = _create_account("owner@example.com", AccountRole.ADMIN)
    student_id = _create_account("requester@example.com", AccountRole.USER)
    _set_session(owner_id, "owner-session")
    _set_session(student_id, "student-session")
    client = TestClient(app)

    class_response = client.post(
        "/admin/judge/academic-classes",
        json={"class_name": "Algorithms"},
        cookies={"session_id": "owner-session"},
    )
    class_id = class_response.json()["class_id"]

    request_response = client.post(
        f"/student/classes/{class_id}/join-requests",
        cookies={"session_id": "student-session"},
    )
    assert request_response.status_code == 200, request_response.text
    assert request_response.json()["status"] == "pending"
    assert client.get(
        f"/student/classes/{class_id}",
        cookies={"session_id": "student-session"},
    ).status_code == 403

    pending_response = client.get(
        f"/admin/judge/academic-classes/{class_id}/join-requests",
        cookies={"session_id": "owner-session"},
    )
    assert pending_response.status_code == 200, pending_response.text
    request_id = pending_response.json()[0]["join_request_id"]

    decision_response = client.patch(
        f"/admin/judge/academic-classes/{class_id}/join-requests/{request_id}",
        json={"status": "approved"},
        cookies={"session_id": "owner-session"},
    )
    assert decision_response.status_code == 200, decision_response.text
    assert client.get(
        f"/student/classes/{class_id}",
        cookies={"session_id": "student-session"},
    ).status_code == 200
    assert client.get(
        "/student/classes",
        cookies={"session_id": "student-session"},
    ).json()[0]["class_id"] == class_id


def test_admins_only_manage_owned_classes_and_students_cannot_create_them():
    owner_id = _create_account("owner2@example.com", AccountRole.ADMIN)
    other_admin_id = _create_account("other-admin@example.com", AccountRole.ADMIN)
    student_id = _create_account("ordinary-student@example.com", AccountRole.USER)
    _set_session(owner_id, "owner2-session")
    _set_session(other_admin_id, "other-admin-session")
    _set_session(student_id, "ordinary-student-session")
    client = TestClient(app)

    class_response = client.post(
        "/admin/judge/academic-classes",
        json={"class_name": "Owned class"},
        cookies={"session_id": "owner2-session"},
    )
    class_id = class_response.json()["class_id"]
    assert [item["class_id"] for item in client.get(
        "/admin/judge/academic-classes",
        cookies={"session_id": "other-admin-session"},
    ).json()] == []
    assert client.get(
        f"/admin/judge/academic-classes/{class_id}",
        cookies={"session_id": "other-admin-session"},
    ).status_code == 403
    assert client.post(
        f"/admin/judge/academic-classes/{class_id}/problems/create",
        json={
            "problem_name": "Unauthorized",
            "time_limit": 1,
            "memory_limit": 256,
        },
        cookies={"session_id": "other-admin-session"},
    ).status_code == 403
    assert client.post(
        "/admin/judge/academic-classes",
        json={"class_name": "Should not exist"},
        cookies={"session_id": "ordinary-student-session"},
    ).status_code == 403

    with TestingSessionLocal() as db:
        other_admin = Admin(account_id=other_admin_id, is_active=True)
        db.add(other_admin)
        db.commit()
        db.refresh(other_admin)
        db.add(ManageClass(class_id=class_id, admin_id=other_admin.admin_id))
        db.commit()

    assert client.get(
        f"/admin/judge/academic-classes/{class_id}",
        cookies={"session_id": "other-admin-session"},
    ).status_code == 200

    request_response = client.post(
        f"/student/classes/{class_id}/join-requests",
        cookies={"session_id": "ordinary-student-session"},
    )
    assert request_response.status_code == 200, request_response.text
    with TestingSessionLocal() as db:
        join_request = db.scalar(select(ClassJoinRequest))
        request_id = join_request.join_request_id

    assert client.patch(
        f"/admin/judge/academic-classes/{class_id}/join-requests/{request_id}",
        json={"status": "approved"},
        cookies={"session_id": "other-admin-session"},
    ).status_code == 200


def test_enrolled_student_can_submit_source_code_for_class_problem(monkeypatch):
    admin_id = _create_account("submit-admin@example.com", AccountRole.ADMIN)
    student_id = _create_account("submit-student@example.com", AccountRole.USER)
    _set_session(admin_id, "submit-admin-session")
    _set_session(student_id, "submit-student-session")
    with TestingSessionLocal() as db:
        db.add(Language(language_id=71, name="Python (3.8.1)"))
        db.commit()
    monkeypatch.setattr(
        judge_admin,
        "_run_judge0",
        lambda source_code, language_id, testcase, time_limit, memory_limit, **kwargs: {
            "status": {"id": 3, "description": "Accepted"},
            "stdout": "5\n",
        },
    )
    client = TestClient(app)

    class_id = client.post(
        "/admin/judge/academic-classes",
        json={"class_name": "Submission class"},
        cookies={"session_id": "submit-admin-session"},
    ).json()["class_id"]
    problem = client.post(
        f"/admin/judge/academic-classes/{class_id}/problems/create",
        json={
            "problem_name": "Add two numbers",
            "time_limit": 1,
            "memory_limit": 256,
            "testcases": [
                {"input_data": "2 3\n", "expected_output": "5\n", "point": 100},
            ],
        },
        cookies={"session_id": "submit-admin-session"},
    )
    assert problem.status_code == 200, problem.text
    problem = problem.json()
    problem_id = problem["problem_id"]

    now = datetime.now(timezone.utc)
    invalid_contest = client.post(
        f"/admin/judge/academic-classes/{class_id}/contests/create",
        json={
            "contest_name": "Invalid contest",
            "start_time": (now - timedelta(minutes=5)).isoformat(),
            "end_time": (now + timedelta(minutes=30)).isoformat(),
            "problem_ids": [999],
        },
        cookies={"session_id": "submit-admin-session"},
    )
    assert invalid_contest.status_code == 422
    contest_response = client.post(
        f"/admin/judge/academic-classes/{class_id}/contests/create",
        json={
            "contest_name": "Live contest",
            "description": "A timed test",
            "start_time": (now - timedelta(minutes=5)).isoformat(),
            "end_time": (now + timedelta(minutes=30)).isoformat(),
            "problem_ids": [problem_id],
        },
        cookies={"session_id": "submit-admin-session"},
    )
    assert contest_response.status_code == 200, contest_response.text
    contest_id = contest_response.json()["contest_id"]

    submit_url = f"/student/classes/{class_id}/problems/{problem_id}/submissions"
    submission_body = {
        "language_id": 71,
        "source_code": "print(sum(map(int, input().split())))",
        "contest_id": contest_id,
    }
    assert client.post(
        submit_url,
        json=submission_body,
        cookies={"session_id": "submit-student-session"},
    ).status_code == 403

    request_id_response = client.post(
        f"/student/classes/{class_id}/join-requests",
        cookies={"session_id": "submit-student-session"},
    )
    request_id = client.get(
        f"/admin/judge/academic-classes/{class_id}/join-requests",
        cookies={"session_id": "submit-admin-session"},
    ).json()[0]["join_request_id"]
    assert request_id_response.status_code == 200
    assert client.patch(
        f"/admin/judge/academic-classes/{class_id}/join-requests/{request_id}",
        json={"status": "approved"},
        cookies={"session_id": "submit-admin-session"},
    ).status_code == 200

    future_contest = client.post(
        f"/admin/judge/academic-classes/{class_id}/contests/create",
        json={
            "contest_name": "Future contest",
            "start_time": (now + timedelta(days=1)).isoformat(),
            "end_time": (now + timedelta(days=1, hours=1)).isoformat(),
            "problem_ids": [problem_id],
        },
        cookies={"session_id": "submit-admin-session"},
    )
    assert future_contest.status_code == 200, future_contest.text
    assert client.post(
        submit_url,
        json={
            **submission_body,
            "contest_id": future_contest.json()["contest_id"],
        },
        cookies={"session_id": "submit-student-session"},
    ).status_code == 409

    response = client.post(
        submit_url,
        json=submission_body,
        cookies={"session_id": "submit-student-session"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "Accepted"
    assert response.json()["score"] == 100
    contest_detail = client.get(
        f"/student/classes/{class_id}/contests/{contest_id}",
        cookies={"session_id": "submit-student-session"},
    )
    assert contest_detail.status_code == 200, contest_detail.text
    assert contest_detail.json()["can_submit"] is True
    assert contest_detail.json()["problems"][0]["is_solved"] is True
    standings = client.get(
        f"/student/classes/{class_id}/contests/{contest_id}/standings",
        cookies={"session_id": "submit-student-session"},
    )
    assert standings.status_code == 200, standings.text
    assert standings.json()["standings"][0]["is_current_user"] is True
    history = client.get(
        f"/student/classes/{class_id}/submissions",
        cookies={"session_id": "submit-student-session"},
    )
    assert history.status_code == 200, history.text
    assert history.json()[0]["contest_id"] == contest_id
    assert "source_code" not in history.json()[0]
    assert client.get(
        "/student/languages",
        cookies={"session_id": "submit-student-session"},
    ).json()[0]["language_id"] == 71
    with TestingSessionLocal() as db:
        submission = db.query(Submission).one()
        assert submission.source_code == submission_body["source_code"]
        assert submission.contest_id == contest_id


def test_problem_and_contest_inputs_are_validated():
    admin_id = _create_account("validation-admin@example.com", AccountRole.ADMIN)
    _set_session(admin_id, "validation-session")
    client = TestClient(app)

    invalid_problem = client.post(
        "/admin/judge/problems",
        json={
            "problem_name": "Invalid limits",
            "time_limit": 0,
            "memory_limit": 256,
        },
        cookies={"session_id": "validation-session"},
    )
    assert invalid_problem.status_code == 422

    invalid_contest = client.post(
        "/admin/judge/contests",
        json={
            "contest_name": "Invalid schedule",
            "start_time": "2026-10-01T12:00:00Z",
            "end_time": "2026-10-01T10:00:00Z",
        },
        cookies={"session_id": "validation-session"},
    )
    assert invalid_contest.status_code == 422
