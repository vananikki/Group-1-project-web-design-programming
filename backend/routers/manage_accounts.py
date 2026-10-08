from datetime import datetime, timezone

from fastapi import APIRouter, Cookie, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from db.schemas import AccountRoleUpdateIn
from db.session import get_session
from db.tables import Account, AccountRole, Admin, Session as UserSession

router = APIRouter(prefix="/admin/accounts", tags=["account management"])


def get_super_admin(
    session_id: str | None,
    session: Session,
) -> Account:
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
    if account.role != AccountRole.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Không có quyền quản lý tài khoản")

    return account


@router.get("")
def list_accounts(
    session_id: str | None = Cookie(default=None),
    session: Session = Depends(get_session),
):
    get_super_admin(session_id, session)
    accounts = session.scalars(
        select(Account)
        .options(selectinload(Account.admin))
        .order_by(Account.account_id)
    ).all()

    return [
        {
            "account_id": account.account_id,
            "account_code": account.account_code,
            "account_name": account.account_name,
            "account_email": account.account_email,
            "role": account.role.value,
            "admin_active": bool(account.admin and account.admin.is_active),
        }
        for account in accounts
    ]


@router.patch("/{account_id}/role")
def update_account_role(
    account_id: int,
    data: AccountRoleUpdateIn,
    session_id: str | None = Cookie(default=None),
    session: Session = Depends(get_session),
):
    acting_account = get_super_admin(session_id, session)
    account = session.get(Account, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="Tài khoản không tồn tại")

    if account.account_id == acting_account.account_id and data.role != AccountRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=409,
            detail="Không thể tự hạ quyền super admin",
        )

    if account.role == AccountRole.SUPER_ADMIN and data.role != AccountRole.SUPER_ADMIN:
        super_admin_count = session.scalar(
            select(func.count())
            .select_from(Account)
            .where(Account.role == AccountRole.SUPER_ADMIN)
        )
        if super_admin_count <= 1:
            raise HTTPException(
                status_code=409,
                detail="Không thể hạ quyền super admin cuối cùng",
            )

    admin = session.scalar(
        select(Admin).where(Admin.account_id == account.account_id)
    )
    should_be_admin = data.role in {
        AccountRole.ADMIN,
        AccountRole.SUPER_ADMIN,
    }
    if should_be_admin and admin is None:
        admin = Admin(account_id=account.account_id, is_active=True)
        session.add(admin)
    elif admin is not None:
        admin.is_active = should_be_admin

    account.role = data.role
    session.commit()
    session.refresh(account)

    return {
        "account_id": account.account_id,
        "account_code": account.account_code,
        "account_name": account.account_name,
        "account_email": account.account_email,
        "role": account.role.value,
        "admin_active": bool(admin and admin.is_active),
    }
