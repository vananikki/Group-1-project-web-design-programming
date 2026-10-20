
from enum import Enum

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
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.tables_phase1 import Account, Base


# ============================================================
# Problem
# ============================================================

class AccessModifier(str, Enum):
    PRIVATE = "private"
    PUBLIC = "public"


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

    description: Mapped[str | None] = mapped_column(Text)
    input_description: Mapped[str | None] = mapped_column(Text)
    output_description: Mapped[str | None] = mapped_column(Text)
    sample_input: Mapped[str | None] = mapped_column(Text)
    sample_output: Mapped[str | None] = mapped_column(Text)

    time_limit: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    memory_limit: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    created_by: Mapped[int] = mapped_column(
        Integer,
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

    # A problem can belong to multiple contests.
    contest_problems: Mapped[list["ContestProblem"]] = relationship(
        "ContestProblem",
        back_populates="problem",
    )


# ============================================================
# Contest
# ============================================================

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

    description: Mapped[str | None] = mapped_column(Text)

    start_time: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    end_time: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    created_by: Mapped[int] = mapped_column(
        Integer,
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

    @property
    def problem_count(self) -> int:
        """Number of problems currently loaded for this contest."""
        return len(self.contest_problems)


# ============================================================
# ContestProblem
# ============================================================

class ContestProblem(Base):
    __tablename__ = "contest_problem"

    __table_args__ = (
        # A defined position can be used only once per contest.
        # PostgreSQL allows multiple NULL values in this unique constraint.
        UniqueConstraint(
            "contest_id",
            "problem_order",
            name="uq_contest_problem_order",
        ),

        # NULL means that the position has not been assigned yet.
        CheckConstraint(
            "problem_order IS NULL OR "
            "(problem_order BETWEEN 1 AND 20)",
            name="ck_contest_problem_order",
        ),
    )

    # Composite primary key: the same problem cannot be added
    # twice to the same contest.
    contest_id: Mapped[int] = mapped_column(
        ForeignKey("contest.contest_id", ondelete="CASCADE"),
        primary_key=True,
    )

    problem_id: Mapped[int] = mapped_column(
        ForeignKey("problem.problem_id"),
        primary_key=True,
    )

    # 1..20, or None when the position is not yet assigned.
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
