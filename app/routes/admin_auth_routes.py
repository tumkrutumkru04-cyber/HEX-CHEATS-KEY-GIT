from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import get_settings
from app.models.admin import Admin
from app.security.admin_auth import verify_password, create_session_token, COOKIE_NAME

router = APIRouter(tags=["admin-auth"])
templates = Jinja2Templates(directory="app/admin/templates")
settings = get_settings()


@router.get("/admin/login")
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@router.post("/admin/login")
async def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    admin = db.query(Admin).filter(Admin.username == username).first()
    if not admin or not verify_password(password, admin.password_hash):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid username or password."},
            status_code=401,
        )

    token = create_session_token(admin.id, admin.username)
    response = RedirectResponse(url="/admin/dashboard", status_code=303)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.ENV == "production",
        samesite="lax",
        max_age=settings.SESSION_MAX_AGE_SECONDS,
    )
    return response


@router.get("/admin/logout")
async def logout():
    response = RedirectResponse(url="/admin/login", status_code=303)
    response.delete_cookie(COOKIE_NAME)
    return response
