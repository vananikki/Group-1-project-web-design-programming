
import os
from enum import Enum
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum as SQLAlchemyEnum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.tables_phase1 import Base, Account


# ============================================================
# Database configuration
# ============================================================

# File: backend/db/initialize/models.py
# .env: backend/db/.env
DB_DIRECTORY = Path(__file__).resolve().parents[1]
load_dotenv(DB_DIRECTORY / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        f"Không tìm thấy DATABASE_URL trong {DB_DIRECTORY / '.env'}"
    )


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

    # Time limit: seconds, integer values from 1 to 9.
    time_limit: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # Memory limit: MB, from 1 to 1024.
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

    # Account that created this problem.
    creator: Mapped["Account"] = relationship(
        "Account",
        foreign_keys=[created_by],
        back_populates="created_problems",
    )



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

    # Account that created this contest.
    creator: Mapped["Account"] = relationship(
        "Account",
        foreign_keys=[created_by],
        back_populates="created_contests",
    )
