from __future__ import annotations

import base64
import os
import time
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import APIRouter, Cookie, Depends, HTTPException
from sqlalchemy import select, or_
from sqlalchemy.orm import Session, selectinload

from db.schemas import (
    AcademicClassContestIn,
    ClassContestCreateIn,
    AcademicClassCreateIn,
    AcademicClassProblemIn,
    AcademicClassStudentIn,
    ClassJoinDecisionIn,
    ContestCreateIn,
    ContestProblemIn,
    ProblemCreateIn,
    ProblemUpdateIn,
    StudentSubmissionIn,
)
from db.session import get_session
from db.tables_phase1 import (
    Account,
    AccountRole,
    Admin,
    AcademicClass,
    ClassJoinRequest,
    ManageClass,
    Session as UserSession,
    Student,
    StudentClass,
)
from db.tables_phase2 import (
    AccessModifier,
    AcademicClassContest,
    AcademicClassProblem,
    Contest,
    ContestProblem,
    Language,
    Problem,
    Submission,
    Testcase,
    add_problem_to_contest,
)

router = APIRouter(prefix="/admin/judge", tags=["judge admin"])
student_router = APIRouter(prefix="/student", tags=["student"])


def _run_judge0(
    source_code: str,
    language_id: int,
    testcase: Testcase,
    time_limit: int,
    memory_limit: int,
    deadline: float | None = None,
) -> dict[str, Any]:
    judge_url = os.getenv("JUDGE0_URL", "http://localhost:2358").rstrip("/")
    deadline = deadline or time.monotonic() + 15
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError("Judge0 grading exceeded the 45-second request limit")
    encoded_payload = {
        "source_code": base64.b64encode(source_code.encode()).decode(),
        "language_id": language_id,
        "stdin": base64.b64encode(testcase.input_data.encode()).decode(),
        "cpu_time_limit": time_limit,
        "memory_limit": memory_limit * 1024,
    }

    with httpx.Client(timeout=httpx.Timeout(5.0)) as client:
        response = client.post(
            f"{judge_url}/submissions",
            params={"base64_encoded": "true", "wait": "false"},
            json=encoded_payload,
            timeout=max(0.1, min(5.0, remaining)),
        )
        response.raise_for_status()
        token = response.json().get("token")
        if not isinstance(token, str) or not token:
            raise ValueError("Judge0 did not return a submission token")

        while time.monotonic() < deadline:
            remaining = deadline - time.monotonic()
            result_response = client.get(
                f"{judge_url}/submissions/{token}",
                params={"base64_encoded": "true"},
                timeout=max(0.1, min(2.0, remaining)),
            )
            result_response.raise_for_status()
            result = result_response.json()
            if not isinstance(result, dict) or not isinstance(result.get("status"), dict):
                raise ValueError("Judge0 returned an invalid result")
            status_id = result["status"].get("id")
            if isinstance(status_id, int) and status_id >= 3:
                for field in ("stdout", "stderr", "compile_output"):
                    value = result.get(field)
                    result[field] = (
                        base64.b64decode(value).decode("utf-8", errors="replace")
                        if value
                        else ""
                    )
                return result
            time.sleep(min(0.5, max(0, deadline - time.monotonic())))

    raise TimeoutError("Judge0 grading exceeded the 45-second request limit")


def _require_admin_account(session_id: str | None, session: Session) -> Account:
    if session_id is None:
        raise HTTPException(status_code=401, detail="Chưa đăng nhập")

    user_session = session.get(UserSession, session_id)
    if user_session is None:
        raise HTTPException(status_code=401, detail="Session không hợp lệ")

    expires_at = user_session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Session đã hết hạn")

    account = session.get(Account, user_session.account_id)
    if account is None:
        raise HTTPException(status_code=401, detail="Tài khoản không tồn tại")
    if not account.is_active:
        raise HTTPException(status_code=403, detail="Tài khoản chưa được kích hoạt")

    if account.role not in {AccountRole.ADMIN, AccountRole.SUPER_ADMIN}:
        raise HTTPException(status_code=403, detail="Bạn không có quyền quản lý judge")

    admin = session.scalar(select(Admin).where(Admin.account_id == account.account_id))
    if admin is not None and not admin.is_active:
        raise HTTPException(status_code=403, detail="Tài khoản quản trị đã bị vô hiệu hóa")

    return account


def _require_student_account(session_id: str | None, session: Session) -> Account:
    if session_id is None:
        raise HTTPException(status_code=401, detail="Chưa đăng nhập")

    user_session = session.get(UserSession, session_id)
    if user_session is None:
        raise HTTPException(status_code=401, detail="Session không hợp lệ")

    expires_at = user_session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Session đã hết hạn")

    account = session.get(Account, user_session.account_id)
    if account is None or not account.is_active:
        raise HTTPException(status_code=403, detail="Tài khoản không hoạt động")
    if account.role != AccountRole.USER:
        raise HTTPException(status_code=403, detail="Chức năng này dành cho học viên")
    return account


def _class_owner_account_id(class_id: int, session: Session) -> int | None:
    return session.scalar(
        select(Admin.account_id)
        .join(ManageClass, ManageClass.admin_id == Admin.admin_id)
        .where(ManageClass.class_id == class_id)
        .order_by(ManageClass.manage_id)
        .limit(1)
    )


def _require_class_manager(
    account: Account,
    class_id: int,
    session: Session,
) -> bool:
    if session.get(AcademicClass, class_id) is None:
        raise HTTPException(status_code=404, detail="Academic class không tồn tại")
    if account.role == AccountRole.SUPER_ADMIN:
        return _class_owner_account_id(class_id, session) == account.account_id

    admin = session.scalar(select(Admin).where(Admin.account_id == account.account_id))
    if admin is None:
        raise HTTPException(status_code=403, detail="Bạn chưa được cấp quyền quản lý lớp này")
    assignment = session.scalar(
        select(ManageClass).where(
            ManageClass.class_id == class_id,
            ManageClass.admin_id == admin.admin_id,
        )
    )
    if assignment is None:
        raise HTTPException(status_code=403, detail="Bạn chưa được cấp quyền quản lý lớp này")
    return _class_owner_account_id(class_id, session) == account.account_id


def _parse_datetime(value: str | None, field_name: str) -> datetime:
    if value is None or value == "":
        raise HTTPException(status_code=422, detail=f"{field_name} là bắt buộc")

    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"{field_name} không hợp lệ") from exc

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _serialize_problem(problem: Problem) -> dict[str, Any]:
    return {
        "problem_id": problem.problem_id,
        "problem_name": problem.problem_name,
        "description": problem.description,
        "input_description": problem.input_description,
        "output_description": problem.output_description,
        "time_limit": problem.time_limit,
        "memory_limit": problem.memory_limit,
        "access_modifier": problem.access_modifier.value,
        "created_by": problem.created_by,
        "creator_name": problem.creator.account_name if problem.creator else None,
        "created_at": problem.created_at.isoformat() if problem.created_at else None,
    }


def _serialize_contest(contest: Contest) -> dict[str, Any]:
    return {
        "contest_id": contest.contest_id,
        "contest_name": contest.contest_name,
        "description": contest.description,
        "start_time": _as_utc(contest.start_time).isoformat(),
        "end_time": _as_utc(contest.end_time).isoformat(),
        "created_by": contest.created_by,
        "creator_name": contest.creator.account_name if contest.creator else None,
        "created_at": contest.created_at.isoformat() if contest.created_at else None,
        "status": _contest_status(contest),
    }


def _contest_status(contest: Contest) -> str:
    now = datetime.now(timezone.utc)
    start_time = _as_utc(contest.start_time)
    end_time = _as_utc(contest.end_time)
    if now < start_time:
        return "upcoming"
    if now <= end_time:
        return "active"
    return "finished"


@router.get("/problems")
def list_problems(
    session_id: str | None = Cookie(default=None),
    session: Session = Depends(get_session),
):
    account = _require_admin_account(session_id, session)

    stmt = select(Problem).options(selectinload(Problem.creator)).order_by(Problem.problem_id.desc())
    if account.role != AccountRole.SUPER_ADMIN:
        stmt = stmt.where(
            or_(
                Problem.created_by == account.account_id,
                Problem.access_modifier == AccessModifier.PUBLIC,
            )
        )

    problems = session.scalars(stmt).all()
    return [_serialize_problem(problem) for problem in problems]


@router.post("/problems")
def create_problem(
    payload: ProblemCreateIn,
    session_id: str | None = Cookie(default=None),
    session: Session = Depends(get_session),
):
    account = _require_admin_account(session_id, session)

    problem = Problem(
        problem_name=payload.problem_name,
        description=payload.description or None,
        input_description=payload.input_description or None,
        output_description=payload.output_description or None,
        time_limit=payload.time_limit,
        memory_limit=payload.memory_limit,
        created_by=account.account_id,
        access_modifier=AccessModifier(payload.access_modifier),
        testcases=[
            Testcase(
                input_data=testcase.input_data,
                expected_output=testcase.expected_output,
                point=testcase.point,
            )
            for testcase in payload.testcases
        ],
    )

    session.add(problem)
    session.commit()
    session.refresh(problem)
    return _serialize_problem(problem)


@router.patch("/problems/{problem_id}")
def update_problem(
    problem_id: int,
    payload: ProblemUpdateIn,
    session_id: str | None = Cookie(default=None),
    session: Session = Depends(get_session),
):
    account = _require_admin_account(session_id, session)
    problem = session.get(Problem, problem_id)
    if problem is None:
        raise HTTPException(status_code=404, detail="Problem không tồn tại")

    if account.role != AccountRole.SUPER_ADMIN and problem.created_by != account.account_id:
        raise HTTPException(status_code=403, detail="Bạn chỉ có thể sửa problem của chính mình")

    updates = payload.model_dump(exclude_unset=True)
    if "problem_name" in updates and updates["problem_name"] is not None:
        problem.problem_name = updates["problem_name"]
    if "description" in updates:
        problem.description = updates["description"] or None
    if "input_description" in updates:
        problem.input_description = updates["input_description"] or None
    if "output_description" in updates:
        problem.output_description = updates["output_description"] or None
    if "time_limit" in updates and updates["time_limit"] is not None:
        problem.time_limit = updates["time_limit"]
    if "memory_limit" in updates and updates["memory_limit"] is not None:
        problem.memory_limit = updates["memory_limit"]
    if "access_modifier" in updates and updates["access_modifier"] is not None:
        problem.access_modifier = AccessModifier(updates["access_modifier"])
    if "testcases" in updates and updates["testcases"] is not None:
        problem.testcases = [
            Testcase(
                input_data=testcase["input_data"],
                expected_output=testcase["expected_output"],
                point=testcase["point"],
            )
            for testcase in updates["testcases"]
        ]

    session.commit()
    session.refresh(problem)
    return _serialize_problem(problem)


@router.get("/academic-classes")
def list_academic_classes(
    session_id: str | None = Cookie(default=None),
    session: Session = Depends(get_session),
):
    account = _require_admin_account(session_id, session)
    query = select(AcademicClass).order_by(AcademicClass.class_id.desc())
    if account.role != AccountRole.SUPER_ADMIN:
        query = (
            query.outerjoin(ManageClass, ManageClass.class_id == AcademicClass.class_id)
            .outerjoin(Admin, Admin.admin_id == ManageClass.admin_id)
            .where(
                or_(
                    Admin.account_id == account.account_id,
                    ManageClass.manage_id.is_(None),
                )
            )
        )
    classes = session.scalars(query).unique().all()
    return [
        {
            "class_id": academic_class.class_id,
            "class_name": academic_class.class_name,
            "is_owner": _class_owner_account_id(academic_class.class_id, session) == account.account_id,
            "is_claimable": _class_owner_account_id(academic_class.class_id, session) is None,
        }
        for academic_class in classes
    ]


@router.post("/academic-classes/{class_id}/claim")
def claim_unowned_class(
    class_id: int,
    session_id: str | None = Cookie(default=None),
    session: Session = Depends(get_session),
):
    account = _require_admin_account(session_id, session)
    if account.role not in {AccountRole.ADMIN, AccountRole.SUPER_ADMIN}:
        raise HTTPException(status_code=403, detail="Chỉ quản trị viên lớp mới có thể nhận lớp chưa có chủ")

    academic_class = session.scalar(
        select(AcademicClass)
        .where(AcademicClass.class_id == class_id)
        .with_for_update()
    )
    if academic_class is None:
        raise HTTPException(status_code=404, detail="Academic class không tồn tại")
    if _class_owner_account_id(class_id, session) is not None:
        raise HTTPException(status_code=409, detail="Lớp này đã có người quản lý")

    admin = session.scalar(select(Admin).where(Admin.account_id == account.account_id))
    if admin is None:
        admin = Admin(account_id=account.account_id, is_active=True)
        session.add(admin)
        session.flush()
    session.add(ManageClass(class_id=class_id, admin_id=admin.admin_id))
    session.commit()
    return {"class_id": class_id, "class_name": academic_class.class_name}


@router.get("/academic-classes/{class_id}")
def get_academic_class_detail(
    class_id: int,
    session_id: str | None = Cookie(default=None),
    session: Session = Depends(get_session),
):
    account = _require_admin_account(session_id, session)

    academic_class = session.scalar(
        select(AcademicClass)
        .options(
            selectinload(AcademicClass.student_classes)
            .selectinload(StudentClass.student)
            .selectinload(Student.account)
        )
        .where(AcademicClass.class_id == class_id)
    )
    if academic_class is None:
        raise HTTPException(status_code=404, detail="Academic class không tồn tại")
    is_owner = _require_class_manager(account, class_id, session)

    problems = []
    for item in sorted(academic_class.class_problems, key=lambda x: x.problem_id):
        problem = item.problem
        problems.append(
            {
                "problem_id": problem.problem_id,
                "problem_name": problem.problem_name,
                "access_modifier": problem.access_modifier.value,
                "is_required": item.is_required,
            }
        )

    contests = []
    for item in sorted(academic_class.class_contests, key=lambda x: x.contest_id):
        contest = item.contest
        contests.append(
            {
                "contest_id": contest.contest_id,
                "contest_name": contest.contest_name,
                "start_time": _as_utc(contest.start_time).isoformat(),
                "end_time": _as_utc(contest.end_time).isoformat(),
                "status": _contest_status(contest),
            }
        )

    students = [
        {
            "student_id": item.student.student_id,
            "account_id": item.student.account_id,
            "account_name": item.student.account.account_name,
            "account_email": item.student.account.account_email,
        }
        for item in sorted(academic_class.student_classes, key=lambda x: x.student_id)
    ]

    return {
        "class_id": academic_class.class_id,
        "class_name": academic_class.class_name,
        "problems": problems,
        "contests": contests,
        "students": students,
        "is_owner": is_owner,
        "owner_account_id": _class_owner_account_id(class_id, session),
    }


@router.post("/academic-classes")
def create_academic_class(
    payload: AcademicClassCreateIn,
    session_id: str | None = Cookie(default=None),
    session: Session = Depends(get_session),
):
    account = _require_admin_account(session_id, session)

    academic_class = AcademicClass(class_name=payload.class_name)
    session.add(academic_class)
    admin = session.scalar(select(Admin).where(Admin.account_id == account.account_id))
    if admin is None:
        admin = Admin(account_id=account.account_id, is_active=True)
        session.add(admin)
        session.flush()
    academic_class.manage_classes.append(ManageClass(admin=admin))
    session.commit()
    session.refresh(academic_class)
    return {"class_id": academic_class.class_id, "class_name": academic_class.class_name}


@router.get("/academic-classes/{class_id}/managers")
def list_class_managers(
    class_id: int,
    session_id: str | None = Cookie(default=None),
    session: Session = Depends(get_session),
):
    account = _require_admin_account(session_id, session)
    _require_class_manager(account, class_id, session)
    assignments = session.scalars(
        select(ManageClass)
        .options(selectinload(ManageClass.admin).selectinload(Admin.account))
        .where(ManageClass.class_id == class_id)
        .order_by(ManageClass.manage_id)
    ).all()
    return [
        {
            "account_id": item.admin.account_id,
            "account_name": item.admin.account.account_name,
            "account_email": item.admin.account.account_email,
            "is_owner": item.admin.account_id == _class_owner_account_id(class_id, session),
        }
        for item in assignments
    ]


@router.post("/academic-classes/{class_id}/managers")
def add_class_manager(
    class_id: int,
    payload: AcademicClassStudentIn,
    session_id: str | None = Cookie(default=None),
    session: Session = Depends(get_session),
):
    account = _require_admin_account(session_id, session)
    is_owner = _require_class_manager(account, class_id, session)
    if not is_owner and account.role != AccountRole.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Chỉ chủ lớp mới có thể thay đổi quyền quản lý")

    manager_account = session.get(Account, payload.account_id)
    if manager_account is None or manager_account.role != AccountRole.ADMIN:
        raise HTTPException(status_code=404, detail="Chỉ có thể thêm tài khoản quản trị đang hoạt động")
    if not manager_account.is_active:
        raise HTTPException(status_code=409, detail="Tài khoản quản trị chưa được kích hoạt")

    admin = session.scalar(select(Admin).where(Admin.account_id == manager_account.account_id))
    if admin is None:
        admin = Admin(account_id=manager_account.account_id, is_active=True)
        session.add(admin)
        session.flush()
    if not admin.is_active:
        raise HTTPException(status_code=409, detail="Tài khoản quản trị không có quyền hoạt động")
    if session.scalar(
        select(ManageClass).where(
            ManageClass.class_id == class_id,
            ManageClass.admin_id == admin.admin_id,
        )
    ):
        raise HTTPException(status_code=409, detail="Quản trị viên đã có quyền trong lớp")

    session.add(ManageClass(class_id=class_id, admin_id=admin.admin_id))
    session.commit()
    return {"class_id": class_id, "account_id": manager_account.account_id}


@router.delete("/academic-classes/{class_id}/managers/{account_id}")
def remove_class_manager(
    class_id: int,
    account_id: int,
    session_id: str | None = Cookie(default=None),
    session: Session = Depends(get_session),
):
    account = _require_admin_account(session_id, session)
    is_owner = _require_class_manager(account, class_id, session)
    if not is_owner and account.role != AccountRole.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Chỉ chủ lớp mới có thể thay đổi quyền quản lý")
    if account_id == _class_owner_account_id(class_id, session):
        raise HTTPException(status_code=409, detail="Không thể gỡ quyền của chủ lớp")

    admin = session.scalar(select(Admin).where(Admin.account_id == account_id))
    assignment = session.scalar(
        select(ManageClass).where(
            ManageClass.class_id == class_id,
            ManageClass.admin_id == admin.admin_id if admin else False,
        )
    )
    if assignment is None:
        raise HTTPException(status_code=404, detail="Quản trị viên không quản lý lớp này")
    session.delete(assignment)
    session.commit()
    return {"class_id": class_id, "account_id": account_id}


@student_router.get("/classes")
def list_student_classes(
    session_id: str | None = Cookie(default=None),
    session: Session = Depends(get_session),
):
    account = _require_student_account(session_id, session)
    student = session.scalar(select(Student).where(Student.account_id == account.account_id))
    if student is None:
        return []
    memberships = session.scalars(
        select(StudentClass)
        .options(selectinload(StudentClass.academic_class))
        .where(StudentClass.student_id == student.student_id)
        .order_by(StudentClass.class_id)
    ).all()
    return [
        {
            "class_id": item.class_id,
            "class_name": item.academic_class.class_name,
        }
        for item in memberships
    ]


@student_router.get("/available-classes")
def list_available_classes(
    session_id: str | None = Cookie(default=None),
    session: Session = Depends(get_session),
):
    account = _require_student_account(session_id, session)
    student = session.scalar(select(Student).where(Student.account_id == account.account_id))
    memberships = set()
    requests = {}
    if student is not None:
        memberships = set(
            session.scalars(
                select(StudentClass.class_id).where(StudentClass.student_id == student.student_id)
            ).all()
        )
        requests = {
            item.class_id: item.status
            for item in session.scalars(
                select(ClassJoinRequest).where(ClassJoinRequest.student_id == student.student_id)
            ).all()
        }

    classes = session.scalars(select(AcademicClass).order_by(AcademicClass.class_name)).all()
    return [
        {
            "class_id": item.class_id,
            "class_name": item.class_name,
            "membership_status": (
                "joined" if item.class_id in memberships else requests.get(item.class_id)
            ),
        }
        for item in classes
    ]


@student_router.post("/classes/{class_id}/join-requests")
def request_to_join_class(
    class_id: int,
    session_id: str | None = Cookie(default=None),
    session: Session = Depends(get_session),
):
    account = _require_student_account(session_id, session)
    if session.get(AcademicClass, class_id) is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy lớp học")

    student = session.scalar(select(Student).where(Student.account_id == account.account_id))
    if student is None:
        student = Student(account_id=account.account_id)
        session.add(student)
        session.flush()
    if session.scalar(
        select(StudentClass).where(
            StudentClass.class_id == class_id,
            StudentClass.student_id == student.student_id,
        )
    ):
        raise HTTPException(status_code=409, detail="Bạn đã là thành viên của lớp")

    join_request = session.scalar(
        select(ClassJoinRequest).where(
            ClassJoinRequest.class_id == class_id,
            ClassJoinRequest.student_id == student.student_id,
        )
    )
    if join_request is not None:
        if join_request.status == "pending":
            raise HTTPException(status_code=409, detail="Yêu cầu tham gia đang chờ duyệt")
        join_request.status = "pending"
        join_request.requested_at = datetime.now(timezone.utc)
    else:
        join_request = ClassJoinRequest(class_id=class_id, student_id=student.student_id)
        session.add(join_request)
    session.commit()
    return {"class_id": class_id, "status": join_request.status}


@student_router.get("/classes/{class_id}")
def get_student_class(
    class_id: int,
    session_id: str | None = Cookie(default=None),
    session: Session = Depends(get_session),
):
    account = _require_student_account(session_id, session)
    student = session.scalar(select(Student).where(Student.account_id == account.account_id))
    membership = session.scalar(
        select(StudentClass).where(
            StudentClass.class_id == class_id,
            StudentClass.student_id == student.student_id if student else False,
        )
    )
    if membership is None:
        raise HTTPException(status_code=403, detail="Bạn chưa tham gia lớp này")
    academic_class = session.scalar(
        select(AcademicClass)
        .options(
            selectinload(AcademicClass.class_problems).selectinload(AcademicClassProblem.problem),
            selectinload(AcademicClass.class_contests).selectinload(AcademicClassContest.contest),
        )
        .where(AcademicClass.class_id == class_id)
    )
    return {
        "class_id": academic_class.class_id,
        "class_name": academic_class.class_name,
        "problems": [
            {
                "problem_id": item.problem.problem_id,
                "problem_name": item.problem.problem_name,
                "description": item.problem.description,
                "input_description": item.problem.input_description,
                "output_description": item.problem.output_description,
                "time_limit": item.problem.time_limit,
                "memory_limit": item.problem.memory_limit,
                "is_required": item.is_required,
            }
            for item in academic_class.class_problems
        ],
        "contests": [
            {
                "contest_id": item.contest.contest_id,
                "contest_name": item.contest.contest_name,
                "start_time": _as_utc(item.contest.start_time).isoformat(),
                "end_time": _as_utc(item.contest.end_time).isoformat(),
                "status": _contest_status(item.contest),
            }
            for item in academic_class.class_contests
        ],
    }


@student_router.get("/languages")
def list_submission_languages(
    session_id: str | None = Cookie(default=None),
    session: Session = Depends(get_session),
):
    _require_student_account(session_id, session)
    return [
        {"language_id": item.language_id, "name": item.name}
        for item in session.scalars(select(Language).order_by(Language.name)).all()
    ]


@student_router.get("/classes/{class_id}/contests/{contest_id}")
def get_student_contest(
    class_id: int,
    contest_id: int,
    session_id: str | None = Cookie(default=None),
    session: Session = Depends(get_session),
):
    account = _require_student_account(session_id, session)
    student = session.scalar(select(Student).where(Student.account_id == account.account_id))
    if student is None or session.scalar(
        select(StudentClass).where(
            StudentClass.class_id == class_id,
            StudentClass.student_id == student.student_id,
        )
    ) is None:
        raise HTTPException(status_code=403, detail="Bạn chưa tham gia lớp này")
    if session.get(AcademicClassContest, (class_id, contest_id)) is None:
        raise HTTPException(status_code=404, detail="Cuộc thi không thuộc lớp này")
    contest = session.scalar(
        select(Contest)
        .options(
            selectinload(Contest.contest_problems).selectinload(ContestProblem.problem)
        )
        .where(Contest.contest_id == contest_id)
    )
    if contest is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy cuộc thi")
    status = _contest_status(contest)
    now = datetime.now(timezone.utc)
    return {
        "contest_id": contest.contest_id,
        "contest_name": contest.contest_name,
        "description": contest.description,
        "start_time": _as_utc(contest.start_time).isoformat(),
        "end_time": _as_utc(contest.end_time).isoformat(),
        "status": status,
        "can_submit": status == "active",
        "problems": [
            {
                "problem_id": item.problem_id,
                "problem_name": item.problem.problem_name,
                "description": item.problem.description,
                "input_description": item.problem.input_description,
                "output_description": item.problem.output_description,
                "time_limit": item.problem.time_limit,
                "memory_limit": item.problem.memory_limit,
                "problem_order": item.problem_order,
                "is_solved": bool(
                    session.scalar(
                        select(Submission.submission_id).where(
                            Submission.account_id == account.account_id,
                            Submission.contest_id == contest_id,
                            Submission.problem_id == item.problem_id,
                            Submission.status == "Accepted",
                        ).limit(1)
                    )
                ),
            }
            for item in contest.contest_problems
        ],
        "server_time": now.isoformat(),
    }


@student_router.get("/classes/{class_id}/contests/{contest_id}/standings")
def get_student_contest_standings(
    class_id: int,
    contest_id: int,
    session_id: str | None = Cookie(default=None),
    session: Session = Depends(get_session),
):
    account = _require_student_account(session_id, session)
    student = session.scalar(select(Student).where(Student.account_id == account.account_id))
    if student is None or session.scalar(
        select(StudentClass).where(
            StudentClass.class_id == class_id,
            StudentClass.student_id == student.student_id,
        )
    ) is None:
        raise HTTPException(status_code=403, detail="Bạn chưa tham gia lớp này")
    if session.get(AcademicClassContest, (class_id, contest_id)) is None:
        raise HTTPException(status_code=404, detail="Cuộc thi không thuộc lớp này")
    contest = session.get(Contest, contest_id)
    if contest is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy cuộc thi")

    rows = session.execute(
        select(Submission.account_id, Account.account_name, Submission.problem_id,
               Submission.status, Submission.score, Submission.submitted_at)
        .join(Account, Account.account_id == Submission.account_id)
        .where(Submission.contest_id == contest_id)
        .order_by(Submission.submitted_at)
    ).all()
    standings: dict[int, dict[str, Any]] = {}
    for account_id, account_name, problem_id, status, score, submitted_at in rows:
        participant = standings.setdefault(
            account_id,
            {
                "account_id": account_id,
                "account_name": account_name,
                "solved": 0,
                "score": 0,
                "penalty": 0,
                "problems": {},
            },
        )
        problem_score = participant["problems"].setdefault(
            problem_id, {"attempts": 0, "solved": False, "score": 0}
        )
        if not problem_score["solved"]:
            problem_score["attempts"] += 1
        if status == "Accepted" and not problem_score["solved"]:
            problem_score["solved"] = True
            problem_score["score"] = score or 0
            participant["solved"] += 1
            participant["score"] += score or 0
            participant["penalty"] += problem_score["attempts"] - 1

    result = sorted(
        standings.values(),
        key=lambda item: (-item["score"], item["penalty"], item["account_name"].casefold()),
    )
    for rank, item in enumerate(result, start=1):
        item["rank"] = rank
        item["is_current_user"] = item["account_id"] == account.account_id
    return {
        "contest_id": contest_id,
        "contest_name": contest.contest_name,
        "standings": result,
    }


@student_router.get("/classes/{class_id}/submissions")
def list_student_submissions(
    class_id: int,
    session_id: str | None = Cookie(default=None),
    session: Session = Depends(get_session),
):
    account = _require_student_account(session_id, session)
    student = session.scalar(select(Student).where(Student.account_id == account.account_id))
    if student is None or session.scalar(
        select(StudentClass).where(
            StudentClass.class_id == class_id,
            StudentClass.student_id == student.student_id,
        )
    ) is None:
        raise HTTPException(status_code=403, detail="Bạn chưa tham gia lớp này")
    rows = session.execute(
        select(Submission, Problem.problem_name, Contest.contest_name)
        .join(Problem, Problem.problem_id == Submission.problem_id)
        .outerjoin(Contest, Contest.contest_id == Submission.contest_id)
        .join(
            AcademicClassProblem,
            AcademicClassProblem.problem_id == Submission.problem_id,
        )
        .where(
            AcademicClassProblem.class_id == class_id,
            Submission.account_id == account.account_id,
        )
        .order_by(Submission.submitted_at.desc())
        .limit(100)
    ).all()
    return [
        {
            "submission_id": submission.submission_id,
            "problem_id": submission.problem_id,
            "problem_name": problem_name,
            "contest_id": submission.contest_id,
            "contest_name": contest_name,
            "status": submission.status,
            "score": submission.score,
            "submitted_at": _as_utc(submission.submitted_at).isoformat(),
        }
        for submission, problem_name, contest_name in rows
    ]


@student_router.post("/classes/{class_id}/problems/{problem_id}/submissions")
def submit_solution(
    class_id: int,
    problem_id: int,
    payload: StudentSubmissionIn,
    session_id: str | None = Cookie(default=None),
    session: Session = Depends(get_session),
):
    account = _require_student_account(session_id, session)
    student = session.scalar(select(Student).where(Student.account_id == account.account_id))
    if student is None or session.scalar(
        select(StudentClass).where(
            StudentClass.class_id == class_id,
            StudentClass.student_id == student.student_id,
        )
    ) is None:
        raise HTTPException(status_code=403, detail="Bạn chưa tham gia lớp này")

    if session.get(AcademicClassProblem, (class_id, problem_id)) is None:
        raise HTTPException(status_code=404, detail="Bài tập không thuộc lớp này")
    problem = session.get(Problem, problem_id)
    language = session.get(Language, payload.language_id)
    if language is None:
        raise HTTPException(status_code=422, detail="Ngôn ngữ lập trình không hợp lệ")
    testcases = session.scalars(
        select(Testcase)
        .where(Testcase.problem_id == problem_id)
        .order_by(Testcase.testcase_id)
    ).all()
    if not testcases:
        raise HTTPException(status_code=409, detail="Bài tập chưa có test case để chấm")
    if len(testcases) > 100:
        raise HTTPException(status_code=409, detail="Bài tập có quá nhiều test case để chấm")
    contest = None
    if payload.contest_id is not None:
        if session.get(AcademicClassContest, (class_id, payload.contest_id)) is None:
            raise HTTPException(status_code=404, detail="Cuộc thi không thuộc lớp này")
        if session.get(ContestProblem, (payload.contest_id, problem_id)) is None:
            raise HTTPException(status_code=404, detail="Bài tập không thuộc cuộc thi này")
        contest = session.get(Contest, payload.contest_id)
        now = datetime.now(timezone.utc)
        if not (_as_utc(contest.start_time) <= now <= _as_utc(contest.end_time)):
            raise HTTPException(status_code=409, detail="Cuộc thi chưa bắt đầu hoặc đã kết thúc")

    testcase_results = []
    score = 0
    grading_deadline = time.monotonic() + 45
    try:
        for testcase in testcases:
            if time.monotonic() >= grading_deadline:
                raise TimeoutError("Judge0 grading exceeded the 45-second request limit")
            result = _run_judge0(
                payload.source_code,
                language.language_id,
                testcase,
                problem.time_limit,
                problem.memory_limit,
                deadline=grading_deadline,
            )
            status = result.get("status", {})
            passed = (
                status.get("id") == 3
                and str(result.get("stdout") or "").rstrip()
                == testcase.expected_output.rstrip()
            )
            if passed:
                score += testcase.point
            testcase_results.append(
                {
                    "status": status.get("description", "Unknown"),
                    "passed": passed,
                }
            )
            if status.get("id") != 3:
                break
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=503,
            detail="Dịch vụ chấm bài Judge0 hiện không khả dụng",
        ) from exc
    except TimeoutError as exc:
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=502, detail="Phản hồi từ Judge0 không hợp lệ") from exc

    all_passed = len(testcase_results) == len(testcases) and all(
        item["passed"] for item in testcase_results
    )
    submission_status = (
        "Accepted"
        if all_passed
        else next(
            (
                item["status"]
                for item in testcase_results
                if item["status"] != "Accepted"
            ),
            "Wrong Answer",
        )
    )
    submission = Submission(
        problem_id=problem_id,
        account_id=account.account_id,
        language_id=language.language_id,
        contest_id=contest.contest_id if contest else None,
        status=submission_status,
        score=score,
        source_code=payload.source_code,
    )
    session.add(submission)
    session.commit()
    session.refresh(submission)
    return {
        "submission_id": submission.submission_id,
        "status": submission.status,
        "score": score,
        "passed_testcases": sum(item["passed"] for item in testcase_results),
        "total_testcases": len(testcases),
        "testcases": testcase_results,
    }


@router.get("/academic-classes/{class_id}/join-requests")
def list_class_join_requests(
    class_id: int,
    session_id: str | None = Cookie(default=None),
    session: Session = Depends(get_session),
):
    account = _require_admin_account(session_id, session)
    _require_class_manager(account, class_id, session)
    requests = session.scalars(
        select(ClassJoinRequest)
        .options(selectinload(ClassJoinRequest.student).selectinload(Student.account))
        .where(ClassJoinRequest.class_id == class_id, ClassJoinRequest.status == "pending")
        .order_by(ClassJoinRequest.requested_at)
    ).all()
    return [
        {
            "join_request_id": item.join_request_id,
            "account_id": item.student.account_id,
            "account_name": item.student.account.account_name,
            "account_email": item.student.account.account_email,
            "requested_at": item.requested_at.isoformat(),
        }
        for item in requests
    ]


@router.patch("/academic-classes/{class_id}/join-requests/{request_id}")
def decide_class_join_request(
    class_id: int,
    request_id: int,
    payload: ClassJoinDecisionIn,
    session_id: str | None = Cookie(default=None),
    session: Session = Depends(get_session),
):
    account = _require_admin_account(session_id, session)
    _require_class_manager(account, class_id, session)
    join_request = session.get(ClassJoinRequest, request_id)
    if join_request is None or join_request.class_id != class_id:
        raise HTTPException(status_code=404, detail="Không tìm thấy yêu cầu tham gia")
    if join_request.status != "pending":
        raise HTTPException(status_code=409, detail="Yêu cầu này đã được xử lý")

    join_request.status = payload.status
    if payload.status == "approved":
        membership = session.scalar(
            select(StudentClass).where(
                StudentClass.class_id == class_id,
                StudentClass.student_id == join_request.student_id,
            )
        )
        if membership is None:
            session.add(
                StudentClass(class_id=class_id, student_id=join_request.student_id)
            )
    session.commit()
    return {"class_id": class_id, "status": join_request.status}


@router.post("/academic-classes/{class_id}/problems")
def attach_problem_to_class(
    class_id: int,
    payload: AcademicClassProblemIn,
    session_id: str | None = Cookie(default=None),
    session: Session = Depends(get_session),
):
    account = _require_admin_account(session_id, session)

    _require_class_manager(account, class_id, session)

    problem = session.get(Problem, payload.problem_id)
    if problem is None:
        raise HTTPException(status_code=404, detail="Problem không tồn tại")

    if account.role != AccountRole.SUPER_ADMIN and problem.created_by != account.account_id:
        if problem.access_modifier != AccessModifier.PUBLIC:
            raise HTTPException(status_code=403, detail="Bạn chỉ có thể gắn problem public hoặc problem của chính mình")

    existing = session.get(AcademicClassProblem, (class_id, payload.problem_id))
    if existing is not None:
        raise HTTPException(status_code=409, detail="Problem đã nằm trong academic class")

    relation = AcademicClassProblem(
        class_id=class_id,
        problem_id=payload.problem_id,
        is_required=payload.is_required,
    )
    session.add(relation)
    session.commit()
    return {"class_id": class_id, "problem_id": payload.problem_id, "is_required": relation.is_required}


@router.post("/academic-classes/{class_id}/problems/create")
def create_problem_for_class(
    class_id: int,
    payload: ProblemCreateIn,
    session_id: str | None = Cookie(default=None),
    session: Session = Depends(get_session),
):
    account = _require_admin_account(session_id, session)
    _require_class_manager(account, class_id, session)
    problem = Problem(
        problem_name=payload.problem_name,
        description=payload.description or None,
        input_description=payload.input_description or None,
        output_description=payload.output_description or None,
        time_limit=payload.time_limit,
        memory_limit=payload.memory_limit,
        created_by=account.account_id,
        access_modifier=AccessModifier(payload.access_modifier),
        testcases=[
            Testcase(
                input_data=testcase.input_data,
                expected_output=testcase.expected_output,
                point=testcase.point,
            )
            for testcase in payload.testcases
        ],
    )
    session.add(problem)
    session.flush()
    session.add(
        AcademicClassProblem(
            class_id=class_id,
            problem_id=problem.problem_id,
            is_required=False,
        )
    )
    session.commit()
    session.refresh(problem)
    return _serialize_problem(problem)


@router.post("/academic-classes/{class_id}/students")
def add_student_to_class(
    class_id: int,
    payload: AcademicClassStudentIn,
    session_id: str | None = Cookie(default=None),
    session: Session = Depends(get_session),
):
    account = _require_admin_account(session_id, session)

    _require_class_manager(account, class_id, session)

    account = session.get(Account, payload.account_id)
    if account is None or account.role != AccountRole.USER:
        raise HTTPException(status_code=404, detail="Không tìm thấy học viên với account_id này")
    if not account.is_active:
        raise HTTPException(status_code=409, detail="Tài khoản học viên chưa được kích hoạt")

    student = session.scalar(
        select(Student)
        .options(selectinload(Student.account))
        .where(Student.account_id == account.account_id)
    )
    if student is None:
        student = Student(account_id=account.account_id)
        session.add(student)
        session.flush()

    existing = session.scalar(
        select(StudentClass).where(
            StudentClass.class_id == class_id,
            StudentClass.student_id == student.student_id,
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="Học viên đã thuộc academic class")

    session.add(StudentClass(class_id=class_id, student_id=student.student_id))
    session.commit()
    return {
        "class_id": class_id,
        "student_id": student.student_id,
        "account_id": student.account_id,
        "account_name": student.account.account_name,
    }


@router.delete("/academic-classes/{class_id}/students/{account_id}")
def remove_student_from_class(
    class_id: int,
    account_id: int,
    session_id: str | None = Cookie(default=None),
    session: Session = Depends(get_session),
):
    account = _require_admin_account(session_id, session)

    _require_class_manager(account, class_id, session)

    student = session.scalar(
        select(Student).where(Student.account_id == account_id)
    )
    if student is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy học viên với account_id này")

    relation = session.scalar(
        select(StudentClass).where(
            StudentClass.class_id == class_id,
            StudentClass.student_id == student.student_id,
        )
    )
    if relation is None:
        raise HTTPException(status_code=404, detail="Học viên không thuộc academic class")

    session.delete(relation)
    session.commit()
    return {"class_id": class_id, "account_id": account_id}


@router.get("/contests")
def list_contests(
    session_id: str | None = Cookie(default=None),
    session: Session = Depends(get_session),
):
    _require_admin_account(session_id, session)
    contests = session.scalars(
        select(Contest).options(selectinload(Contest.creator)).order_by(Contest.contest_id.desc())
    ).all()
    return [_serialize_contest(contest) for contest in contests]


@router.get("/contests/{contest_id}")
def get_contest_detail(
    contest_id: int,
    session_id: str | None = Cookie(default=None),
    session: Session = Depends(get_session),
):
    _require_admin_account(session_id, session)

    contest = session.get(Contest, contest_id)
    if contest is None:
        raise HTTPException(status_code=404, detail="Contest không tồn tại")

    problems = []
    for item in contest.contest_problems:
        problems.append(
            {
                "problem_id": item.problem_id,
                "problem_name": item.problem.problem_name,
                "problem_order": item.problem_order,
                "access_modifier": item.problem.access_modifier.value,
            }
        )

    now = datetime.now(timezone.utc)
    status = _contest_status(contest)
    return {
        "contest_id": contest.contest_id,
        "contest_name": contest.contest_name,
        "description": contest.description,
        "start_time": _as_utc(contest.start_time).isoformat(),
        "end_time": _as_utc(contest.end_time).isoformat(),
        "created_by": contest.created_by,
        "creator_name": contest.creator.account_name if contest.creator else None,
        "created_at": contest.created_at.isoformat() if contest.created_at else None,
        "status": status,
        "is_active": status == "active",
        "is_out_of_contest": now > _as_utc(contest.end_time),
        "problem_count": len(problems),
        "problems": problems,
    }


@router.post("/contests")
def create_contest(
    payload: ContestCreateIn,
    session_id: str | None = Cookie(default=None),
    session: Session = Depends(get_session),
):
    account = _require_admin_account(session_id, session)

    start_time = _parse_datetime(payload.start_time.isoformat(), "start_time")
    end_time = _parse_datetime(payload.end_time.isoformat(), "end_time")
    if end_time <= start_time:
        raise HTTPException(status_code=422, detail="end_time phải lớn hơn start_time")

    contest = Contest(
        contest_name=payload.contest_name,
        description=payload.description or None,
        start_time=start_time,
        end_time=end_time,
        created_by=account.account_id,
    )
    session.add(contest)
    session.commit()
    session.refresh(contest)
    return _serialize_contest(contest)


@router.post("/contests/{contest_id}/problems")
def add_problem_to_contest_route(
    contest_id: int,
    payload: ContestProblemIn,
    session_id: str | None = Cookie(default=None),
    session: Session = Depends(get_session),
):
    account = _require_admin_account(session_id, session)

    contest = session.get(Contest, contest_id)
    if contest is None:
        raise HTTPException(status_code=404, detail="Contest không tồn tại")

    problem_id = payload.problem_id
    problem = session.get(Problem, problem_id)
    if problem is None:
        raise HTTPException(status_code=404, detail="Problem không tồn tại")

    if account.role != AccountRole.SUPER_ADMIN and problem.created_by != account.account_id:
        if problem.access_modifier != AccessModifier.PUBLIC:
            raise HTTPException(status_code=403, detail="Bạn chỉ có thể thêm problem public hoặc problem của chính mình")

    try:
        item = add_problem_to_contest(
            session,
            contest_id,
            problem_id,
            payload.problem_order,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    session.commit()
    return {"contest_id": contest_id, "problem_id": problem_id, "problem_order": item.problem_order}


@router.post("/academic-classes/{class_id}/contests")
def attach_contest_to_class(
    class_id: int,
    payload: AcademicClassContestIn,
    session_id: str | None = Cookie(default=None),
    session: Session = Depends(get_session),
):
    account = _require_admin_account(session_id, session)
    _require_class_manager(account, class_id, session)

    contest = session.get(Contest, payload.contest_id)
    if contest is None:
        raise HTTPException(status_code=404, detail="Contest không tồn tại")

    existing = session.get(AcademicClassContest, (class_id, payload.contest_id))
    if existing is not None:
        raise HTTPException(status_code=409, detail="Contest đã nằm trong academic class")

    relation = AcademicClassContest(class_id=class_id, contest_id=payload.contest_id)
    session.add(relation)
    session.commit()
    return {"class_id": class_id, "contest_id": payload.contest_id}


@router.post("/academic-classes/{class_id}/contests/create")
def create_class_contest(
    class_id: int,
    payload: ClassContestCreateIn,
    session_id: str | None = Cookie(default=None),
    session: Session = Depends(get_session),
):
    account = _require_admin_account(session_id, session)
    _require_class_manager(account, class_id, session)
    start_time = _parse_datetime(payload.start_time.isoformat(), "start_time")
    end_time = _parse_datetime(payload.end_time.isoformat(), "end_time")
    if end_time <= start_time:
        raise HTTPException(status_code=422, detail="Thời điểm kết thúc phải sau thời điểm bắt đầu")

    class_problem_ids = set(
        session.scalars(
            select(AcademicClassProblem.problem_id).where(
                AcademicClassProblem.class_id == class_id
            )
        ).all()
    )
    if not set(payload.problem_ids).issubset(class_problem_ids):
        raise HTTPException(status_code=422, detail="Chỉ có thể thêm bài tập đã thuộc lớp")

    contest = Contest(
        contest_name=payload.contest_name,
        description=payload.description or None,
        start_time=start_time,
        end_time=end_time,
        created_by=account.account_id,
    )
    session.add(contest)
    session.flush()
    for problem_order, problem_id in enumerate(payload.problem_ids, start=1):
        add_problem_to_contest(session, contest.contest_id, problem_id, problem_order)
    session.add(AcademicClassContest(class_id=class_id, contest_id=contest.contest_id))
    session.commit()
    session.refresh(contest)
    return _serialize_contest(contest)


@router.get("/contests/{contest_id}/standings")
def contest_standings(
    contest_id: int,
    session_id: str | None = Cookie(default=None),
    session: Session = Depends(get_session),
):
    _require_admin_account(session_id, session)

    contest = session.get(Contest, contest_id)
    if contest is None:
        raise HTTPException(status_code=404, detail="Contest không tồn tại")

    rows = session.scalars(
        select(Submission, Account.account_name)
        .join(Account, Account.account_id == Submission.account_id)
        .where(Submission.contest_id == contest_id)
        .order_by(Submission.submitted_at.asc())
    ).all()

    standings: dict[int, dict[str, Any]] = {}
    for submission, account_name in rows:
        participant = standings.setdefault(
            submission.account_id,
            {
                "account_id": submission.account_id,
                "account_name": account_name,
                "solved": 0,
                "attempts": 0,
                "score": 0,
            },
        )
        participant["attempts"] += 1
        if submission.status == "Accepted":
            participant["solved"] += 1
            participant["score"] = max(participant["score"], submission.score or 0)

    result = sorted(standings.values(), key=lambda item: (-item["solved"], item["attempts"], -item["score"]))
    return {"contest_id": contest_id, "contest_name": contest.contest_name, "standings": result}


@router.get("/health")
def health_check():
    return {"status": "ok"}
