from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates

from app.models.admin import Admin
from app.dependencies import get_current_admin

router = APIRouter(prefix="/admin", tags=["admin-pages"])
templates = Jinja2Templates(directory="app/admin/templates")


@router.get("/")
async def admin_root():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/admin/dashboard", status_code=303)


@router.get("/dashboard")
async def dashboard(request: Request, admin: Admin = Depends(get_current_admin)):
    return templates.TemplateResponse("dashboard.html", {"request": request, "admin": admin, "active_page": "dashboard"})


@router.get("/keys")
async def keys_page(request: Request, admin: Admin = Depends(get_current_admin)):
    return templates.TemplateResponse("keys.html", {"request": request, "admin": admin, "active_page": "keys"})


@router.get("/generate")
async def generate_page(request: Request, admin: Admin = Depends(get_current_admin)):
    return templates.TemplateResponse("generate.html", {"request": request, "admin": admin, "active_page": "generate"})


@router.get("/devices")
async def devices_page(request: Request, admin: Admin = Depends(get_current_admin)):
    return templates.TemplateResponse("devices.html", {"request": request, "admin": admin, "active_page": "devices"})


@router.get("/logs")
async def logs_page(request: Request, admin: Admin = Depends(get_current_admin)):
    return templates.TemplateResponse("logs.html", {"request": request, "admin": admin, "active_page": "logs"})


@router.get("/settings")
async def settings_page(request: Request, admin: Admin = Depends(get_current_admin)):
    return templates.TemplateResponse("settings.html", {"request": request, "admin": admin, "active_page": "settings"})
