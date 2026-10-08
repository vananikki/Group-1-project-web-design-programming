from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
)

from db.tables import AccountRole


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
        min_length=8,
        max_length=128,
    )


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