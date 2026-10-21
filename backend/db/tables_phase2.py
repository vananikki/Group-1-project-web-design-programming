
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum as SQLAlchemyEnum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    select,
    text,
    update,
)
from sqlalchemy.orm import Mapped, Session, mapped_column, relationship

if TYPE_CHECKING:
    from db.tables_phase1 import AcademicClass

try:
    from db.tables_phase1 import Account, AcademicClass, Base
except ModuleNotFoundError:
    from tables_phase1 import Account, AcademicClass, Base


# =========================================================
# ENUMS
# =========================================================


class AccessModifier(str, Enum):
    PRIVATE = "private"
    PUBLIC = "public"

class Judge0Language(str, Enum):
    C = "C"
    CPP = "C++"
    JAVA = "Java"
    PYTHON = "Python"
    JAVASCRIPT = "JavaScript"
    CSHARP = "C#"
    GO = "Go"
    RUST = "Rust"
    KOTLIN = "Kotlin"
    SWIFT = "Swift"
    RUBY = "Ruby"
    PHP = "PHP"
    TYPESCRIPT = "TypeScript"
    R = "R"
    PASCAL = "Pascal"
    HASKELL = "Haskell"
    DART = "Dart"
    LUA = "Lua"
    PERL = "Perl"
    SCALA = "Scala"



#======LANGUAGE========

class Language(Base): 
    __tablename__ = "language"

    language_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True,
    )

    solutions: Mapped[list["Solution"]] = relationship(
        "Solution",
        back_populates="language",
        cascade="all, delete-orphan",
    )

    submissions: Mapped[list["Submission"]] = relationship(
        "Submission",
        back_populates="language",
        cascade="all, delete-orphan",
    )




# =========================================================
# PROBLEM
# =========================================================

class Solution(Base): 
    __tablename__ = "solution"

    solution_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    problem_id: Mapped[int] = mapped_column(
        ForeignKey("problem.problem_id"),
        nullable=False,
    )

    language_id: Mapped[int] = mapped_column(
        ForeignKey("language.language_id"),
        nullable=False,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    problem: Mapped["Problem"] = relationship(
        "Problem",
        back_populates="solutions",
    )

    language: Mapped["Language"] = relationship(
        "Language",
        back_populates="solutions",
    )

class Testcase(Base): 
    __tablename__ = "testcase"

    testcase_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    problem_id: Mapped[int] = mapped_column(
        ForeignKey("problem.problem_id"),
        nullable=False,
    )

    point: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    input_data: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    expected_output: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    problem: Mapped["Problem"] = relationship(
        "Problem",
        back_populates="testcases",
    )
    

class Problem(Base):
    __tablename__ = "problem"

    __table_args__ = (
        CheckConstraint(
            "time_limit > 0 AND time_limit <= 10",
            name="ck_problem_time_limit",
        ),
        CheckConstraint(
            "memory_limit > 0 AND memory_limit <= 1024",
            name="ck_problem_memory_limit",
        ),
    )

    problem_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    problem_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    input_description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    output_description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    time_limit: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    memory_limit: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    created_by: Mapped[int] = mapped_column(
        ForeignKey("account.account_id"),
        nullable=False,
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    access_modifier: Mapped[AccessModifier] = mapped_column(
        SQLAlchemyEnum(
            AccessModifier,
            name="access_modifier_enum",
            values_callable=lambda enum_cls: [
                item.value for item in enum_cls
            ],
        ),
        nullable=False,
        default=AccessModifier.PRIVATE,
        server_default=text("'private'"),
    )

    creator: Mapped["Account"] = relationship(
        "Account",
        foreign_keys=[created_by],
        back_populates="created_problems",
    )

    contest_problems: Mapped[list["ContestProblem"]] = relationship(
        "ContestProblem",
        back_populates="problem",
    )

    class_problems: Mapped[list["AcademicClassProblem"]] = relationship(
        "AcademicClassProblem",
        back_populates="problem",
        cascade="all, delete-orphan",
    )

    solutions: Mapped[list["Solution"]] = relationship(
        "Solution",
        back_populates="problem",
        cascade="all, delete-orphan",
    )

    testcases: Mapped[list["Testcase"]] = relationship(
        "Testcase",
        back_populates="problem",
        cascade="all, delete-orphan",
    )

    submissions: Mapped[list["Submission"]] = relationship(
        "Submission",
        back_populates="problem",
    )


# =========================================================
# CONTEST
# =========================================================

class Contest(Base):
    __tablename__ = "contest"

    __table_args__ = (
        CheckConstraint(
            "end_time > start_time",
            name="ck_contest_end_after_start",
        ),
    )

    contest_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    contest_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    start_time: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    end_time: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    created_by: Mapped[int] = mapped_column(
        ForeignKey("account.account_id"),
        nullable=False,
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    creator: Mapped["Account"] = relationship(
        "Account",
        foreign_keys=[created_by],
        back_populates="created_contests",
    )

    contest_problems: Mapped[list["ContestProblem"]] = relationship(
        "ContestProblem",
        back_populates="contest",
        cascade="all, delete-orphan",
        order_by="ContestProblem.problem_order",
    )

    submissions: Mapped[list["Submission"]] = relationship(
        "Submission",
        back_populates="contest",
    )

    class_contests: Mapped[list["AcademicClassContest"]] = relationship(
        "AcademicClassContest",
        back_populates="contest",
        cascade="all, delete-orphan",
    )

    @property
    def problem_count(self) -> int:
        """Số bài trong contest khi relationship đã được tải."""
        return len(self.contest_problems)


# =========================================================
# CONTEST PROBLEM
# =========================================================

MAX_PROBLEMS_PER_CONTEST = 20


class AcademicClassProblem(Base):
    __tablename__ = "academic_class_problem"

    class_id: Mapped[int] = mapped_column(
        ForeignKey("academic_class.class_id", ondelete="CASCADE"),
        primary_key=True,
    )
    problem_id: Mapped[int] = mapped_column(
        ForeignKey("problem.problem_id", ondelete="CASCADE"),
        primary_key=True,
    )
    added_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    is_required: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
    )

    academic_class: Mapped["AcademicClass"] = relationship(
        "AcademicClass",
        back_populates="class_problems",
    )

    problem: Mapped["Problem"] = relationship(
        "Problem",
        back_populates="class_problems",
    )


class AcademicClassContest(Base):
    __tablename__ = "academic_class_contest"

    class_id: Mapped[int] = mapped_column(
        ForeignKey("academic_class.class_id", ondelete="CASCADE"),
        primary_key=True,
    )
    contest_id: Mapped[int] = mapped_column(
        ForeignKey("contest.contest_id", ondelete="CASCADE"),
        primary_key=True,
    )

    added_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    academic_class: Mapped["AcademicClass"] = relationship(
        "AcademicClass",
        back_populates="class_contests",
    )

    contest: Mapped["Contest"] = relationship(
        "Contest",
        back_populates="class_contests",
    )


class ContestProblem(Base):
    __tablename__ = "contest_problem"

    __table_args__ = (
        UniqueConstraint(
            "contest_id",
            "problem_order",
            name="uq_contest_problem_order",
        ),
        CheckConstraint(
            "problem_order IS NULL "
            "OR (problem_order BETWEEN 1 AND 20)",
            name="ck_contest_problem_order",
        ),
    )

    # Khóa chính kép: không thể thêm trùng problem_id
    # trong cùng một contest.
    contest_id: Mapped[int] = mapped_column(
        ForeignKey("contest.contest_id", ondelete="CASCADE"),
        primary_key=True,
    )

    problem_id: Mapped[int] = mapped_column(
        ForeignKey("problem.problem_id"),
        primary_key=True,
    )

    # NULL nghĩa là chưa xác định thứ tự.
    problem_order: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    contest: Mapped["Contest"] = relationship(
        "Contest",
        back_populates="contest_problems",
    )

    problem: Mapped["Problem"] = relationship(
        "Problem",
        back_populates="contest_problems",
    )


# =========================================================
# HELPER: COUNT PROBLEMS
# =========================================================

def get_contest_problem_count(
    session: Session,
    contest_id: int,
) -> int:
    """Đếm số bài hiện có trong contest."""

    return session.scalar(
        select(func.count())
        .select_from(ContestProblem)
        .where(ContestProblem.contest_id == contest_id)
    ) or 0


# =========================================================
# VALIDATION: ADD PROBLEM
# =========================================================

def add_problem_to_contest(
    session: Session,
    contest_id: int,
    problem_id: int,
    problem_order: int | None = None,
) -> ContestProblem:
    """
    Thêm một bài vào contest.

    Khi thêm bài mới, vị trí được kiểm tra theo tổng số bài
    SAU KHI THÊM: 1 <= problem_order <= current_count + 1.

    Để trống problem_order nếu chưa xác định thứ tự.

    Hàm flush nhưng không commit; caller quản lý transaction.
    """

    # Khóa contest để tránh các transaction đồng thời
    # cùng thêm bài vượt quá giới hạn.
    contest = session.scalar(
        select(Contest)
        .where(Contest.contest_id == contest_id)
        .with_for_update()
    )

    if contest is None:
        raise ValueError(
            f"Contest ID {contest_id} không tồn tại."
        )

    # Kiểm tra problem tồn tại.
    if session.get(Problem, problem_id) is None:
        raise ValueError(
            f"Problem ID {problem_id} không tồn tại."
        )

    # Đếm số bài hiện tại.
    current_count = get_contest_problem_count(
        session,
        contest_id,
    )

    if current_count >= MAX_PROBLEMS_PER_CONTEST:
        raise ValueError(
            f"Contest chỉ được có tối đa "
            f"{MAX_PROBLEMS_PER_CONTEST} bài."
        )

    # Khóa chính kép cũng bảo vệ quy tắc không trùng.
    existing_problem = session.get(
        ContestProblem,
        (contest_id, problem_id),
    )

    if existing_problem is not None:
        raise ValueError(
            f"Problem ID {problem_id} đã có trong contest "
            f"{contest_id}."
        )

    # Số bài sau khi thêm bài mới.
    new_count = current_count + 1

    if problem_order is not None:
        # Vị trí hợp lệ từ 1 đến tổng số bài SAU KHI THÊM.
        if not 1 <= problem_order <= new_count:
            raise ValueError(
                f"Vị trí phải nằm trong khoảng 1–{new_count}, "
                "hoặc để trống nếu chưa xác định thứ tự."
            )

        # Kiểm tra vị trí đã được bài khác sử dụng.
        existing_order = session.scalar(
            select(ContestProblem)
            .where(
                ContestProblem.contest_id == contest_id,
                ContestProblem.problem_order == problem_order,
            )
        )

        if existing_order is not None:
            raise ValueError(
                f"Vị trí {problem_order} đã được sử dụng "
                f"trong contest {contest_id}."
            )

    item = ContestProblem(
        contest_id=contest_id,
        problem_id=problem_id,
        problem_order=problem_order,
    )

    session.add(item)
    session.flush()

    return item


# =========================================================
# VALIDATION: UPDATE PROBLEM ORDER
# =========================================================

def update_problem_order(
    session: Session,
    contest_id: int,
    problem_id: int,
    new_order: int | None,
) -> ContestProblem:
    """
    Cập nhật thứ tự của bài đã tồn tại trong contest.

    Khi cập nhật, vị trí được kiểm tra theo tổng số bài
    HIỆN CÓ: 1 <= new_order <= current_count.

    new_order = None nghĩa là bỏ xác định thứ tự.
    """

    # Khóa contest trong transaction.
    contest = session.scalar(
        select(Contest)
        .where(Contest.contest_id == contest_id)
        .with_for_update()
    )

    if contest is None:
        raise ValueError(
            f"Contest ID {contest_id} không tồn tại."
        )

    item = session.get(
        ContestProblem,
        (contest_id, problem_id),
    )

    if item is None:
        raise ValueError(
            f"Problem ID {problem_id} không thuộc contest "
            f"{contest_id}."
        )

    current_count = get_contest_problem_count(
        session,
        contest_id,
    )

    if new_order is not None:
        # Khi cập nhật, dùng số bài HIỆN CÓ, không cộng thêm 1.
        if not 1 <= new_order <= current_count:
            raise ValueError(
                f"Vị trí phải nằm trong khoảng 1–{current_count}, "
                "hoặc để trống nếu chưa xác định thứ tự."
            )

        # Không cho hai bài có cùng vị trí.
        existing_order = session.scalar(
            select(ContestProblem)
            .where(
                ContestProblem.contest_id == contest_id,
                ContestProblem.problem_order == new_order,
                ContestProblem.problem_id != problem_id,
            )
        )

        if existing_order is not None:
            raise ValueError(
                f"Vị trí {new_order} đã được sử dụng "
                f"trong contest {contest_id}."
            )

    item.problem_order = new_order
    session.flush()

    return item

#==== SUBMISSION =====
class Submission(Base): 
    __tablename__ = "submission"

    # One account can create many submissions.
    # Each submission belongs to exactly one account.
    submission_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    problem_id: Mapped[int] = mapped_column(
        ForeignKey("problem.problem_id"),
        nullable=False,
    )

    account_id: Mapped[int] = mapped_column(
        ForeignKey("account.account_id"),
        nullable=False,
    )

    contest_id: Mapped[int | None] = mapped_column(
        ForeignKey("contest.contest_id", ondelete="SET NULL"),
        nullable=True,
    )

    language_id: Mapped[int] = mapped_column(
        ForeignKey("language.language_id"),
        nullable=False,
    )

    submitted_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    source_code: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    score: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    problem: Mapped["Problem"] = relationship(
        "Problem",
        back_populates="submissions",
    )

    contest: Mapped["Contest | None"] = relationship(
        "Contest",
        back_populates="submissions",
    )

    language: Mapped["Language"] = relationship(
        "Language",
        back_populates="submissions",
    )

    account: Mapped["Account"] = relationship(
        "Account",
        back_populates="submissions",
    )
