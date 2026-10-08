from fastapi import APIRouter, Cookie, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import delete
from sqlalchemy.orm import Session

from db.session import get_session
from db.tables import Session as UserSession

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/logout")
def logout_api(
    session_id: str | None = Cookie(default=None),
    session: Session = Depends(get_session),
):
    if session_id is not None:
        session.execute(
            delete(UserSession).where(UserSession.session_id == session_id)
        )
        session.commit()

    response = JSONResponse(
        content={"message": "Đăng xuất thành công"},
    )
    response.delete_cookie(
        key="session_id",
        httponly=True,
        secure=False,
        samesite="lax",
    )
    return response
