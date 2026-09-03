from typing import Optional

from fastapi import Request, HTTPException, status, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.security.admin_auth import COOKIE_NAME, read_session_token
from app.models.admin import Admin


def get_current_admin(request: Request, db: Session = Depends(get_db)) -> Admin:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/admin/login"})

    data = read_session_token(token)
    if not data:
        raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/admin/login"})

    admin = db.query(Admin).filter(Admin.id == data.get("admin_id")).first()
    if not admin:
        raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/admin/login"})

    return admin


def get_current_admin_optional(request: Request, db: Session = Depends(get_db)) -> Optional[Admin]:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    data = read_session_token(token)
    if not data:
        return None
    return db.query(Admin).filter(Admin.id == data.get("admin_id")).first()


def get_client_ip(request: Request) -> str:
    # Respect X-Forwarded-For when behind Railway's proxy
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
