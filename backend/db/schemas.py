import re
from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
)

from db.tables import AccountRole

PASSWORD_REQUIREMENTS_MESSAGE = (
    "Mật khẩu phải có ít nhất 8 ký tự, có chữ và số, 1 ký tự đặc biệt và 1 chữ cái in hoa"
)


def validate_password_strength(raw_password: str) -> str:
    if len(raw_password) < 8:
        raise ValueError(PASSWORD_REQUIREMENTS_MESSAGE)
    if not re.search(r"[A-Za-z]", raw_password):
        raise ValueError(PASSWORD_REQUIREMENTS_MESSAGE)
    if not re.search(r"\d", raw_password):
        raise ValueError(PASSWORD_REQUIREMENTS_MESSAGE)
    if not re.search(r"[^A-Za-z0-9]", raw_password):
        raise ValueError(PASSWORD_REQUIREMENTS_MESSAGE)
    if not re.search(r"[A-Z]", raw_password):
        raise ValueError(PASSWORD_REQUIREMENTS_MESSAGE)
    return raw_password


# =========================================================
# Register
# =========================================================

class RegisterIn(BaseModel):
    account_name: str = Field(
        min_length=3,
        max_length=100,
    )

    account_email: EmailStr

    password: str = Field(
        max_length=128,
    )

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return validate_password_strength(v)


# =========================================================
# Login
# =========================================================

class LoginIn(BaseModel):
    account_email: EmailStr

    password: str = Field(
        min_length=1,
        max_length=128,
    )


class AccountRoleUpdateIn(BaseModel):
    role: AccountRole


class AccountNameUpdateIn(BaseModel):
    account_name: str = Field(
        min_length=3,
        max_length=100,
    )


# =========================================================
# Account Update
# =========================================================

class AccountUpdateIn(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    account_name: str | None = Field(
        default=None,
        min_length=3,
        max_length=100,
    )

    account_email: EmailStr | None = None

    @field_validator(
        "account_name",
        "account_email",
    )
    @classmethod
    def not_null_if_sent(cls, v):
        # Client gửi rõ null thì từ chối
        if v is None:
            raise ValueError("Không được để null")

        return v


# =========================================================
# Account Response
# =========================================================

class AccountOut(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    account_id: int
    account_code: str
    account_name: str
    account_email: EmailStr
    created_at: datetime

    # Không trả password_hash