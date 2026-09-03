from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.admin import Admin
from app.models.license import License, LicenseStatus
from app.models.device import Device
from app.models.log import Log
from app.dependencies import get_current_admin
from pydantic import BaseModel
from app.schemas import GenerateKeysRequest, KeyActionRequest, ExtendExpiryRequest


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
from app.services import license_service
from app.services.device_service import reset_device
from app.security.admin_auth import hash_password, verify_password

router = APIRouter(prefix="/admin/api", tags=["admin-api"])


# ---------------- Dashboard stats ----------------

@router.get("/stats")
async def get_stats(db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)):
    total_keys = db.query(License).count()
    now = datetime.utcnow()

    banned = db.query(License).filter(License.status == LicenseStatus.BANNED).count()
    inactive = db.query(License).filter(License.status == LicenseStatus.INACTIVE).count()
    expired = db.query(License).filter(
        License.status == LicenseStatus.ACTIVE,
        License.expires_at.isnot(None),
        License.expires_at < now,
    ).count()
    active = db.query(License).filter(
        License.status == LicenseStatus.ACTIVE,
        or_(License.expires_at.is_(None), License.expires_at >= now),
    ).count()

    devices = db.query(Device).count()
    recent_requests = db.query(Log).order_by(Log.created_at.desc()).limit(10).all()

    return {
        "total_keys": total_keys,
        "active_keys": active,
        "expired_keys": expired,
        "banned_keys": banned,
        "inactive_keys": inactive,
        "registered_devices": devices,
        "recent_requests": [l.to_dict() for l in recent_requests],
    }


# ---------------- License keys ----------------

@router.get("/keys")
async def list_keys(
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
    search: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    q = db.query(License)

    if search:
        q = q.filter(License.license_key.ilike(f"%{search}%"))

    if status_filter and status_filter != "ALL":
        now = datetime.utcnow()
        if status_filter == "EXPIRED":
            q = q.filter(
                License.status == LicenseStatus.ACTIVE,
                License.expires_at.isnot(None),
                License.expires_at < now,
            )
        elif status_filter == "ACTIVE":
            q = q.filter(
                License.status == LicenseStatus.ACTIVE,
                or_(License.expires_at.is_(None), License.expires_at >= now),
            )
        else:
            q = q.filter(License.status == status_filter)

    total = q.count()
    items = (
        q.order_by(License.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size),
        "items": [item.to_dict() for item in items],
    }


@router.post("/keys/generate")
async def generate_keys(
    body: GenerateKeysRequest,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    try:
        created = license_service.create_licenses(
            db=db,
            quantity=body.quantity,
            prefix=body.prefix,
            duration_type=body.duration_type,
            custom_hours=body.custom_hours,
            custom_days=body.custom_days,
            note=body.note,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {"created": [lic.to_dict() for lic in created]}


def _get_license_or_404(db: Session, license_id: str) -> License:
    lic = db.query(License).filter(License.id == license_id).first()
    if not lic:
        raise HTTPException(status_code=404, detail="License not found")
    return lic


@router.post("/keys/activate")
async def activate_key(body: KeyActionRequest, db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)):
    lic = _get_license_or_404(db, body.license_id)
    lic.status = LicenseStatus.ACTIVE
    db.commit()
    return {"ok": True, "license": lic.to_dict()}


@router.post("/keys/deactivate")
async def deactivate_key(body: KeyActionRequest, db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)):
    lic = _get_license_or_404(db, body.license_id)
    lic.status = LicenseStatus.INACTIVE
    db.commit()
    return {"ok": True, "license": lic.to_dict()}


@router.post("/keys/ban")
async def ban_key(body: KeyActionRequest, db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)):
    lic = _get_license_or_404(db, body.license_id)
    lic.status = LicenseStatus.BANNED
    db.commit()
    return {"ok": True, "license": lic.to_dict()}


@router.post("/keys/extend")
async def extend_key(body: ExtendExpiryRequest, db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)):
    lic = _get_license_or_404(db, body.license_id)
    if lic.expires_at is None:
        raise HTTPException(status_code=400, detail="Cannot extend a lifetime key")

    base = lic.expires_at if lic.expires_at > datetime.utcnow() else datetime.utcnow()
    if body.additional_hours:
        base += timedelta(hours=body.additional_hours)
    if body.additional_days:
        base += timedelta(days=body.additional_days)
    lic.expires_at = base
    db.commit()
    return {"ok": True, "license": lic.to_dict()}


@router.post("/keys/reset-device")
async def reset_key_device(body: KeyActionRequest, db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)):
    lic = _get_license_or_404(db, body.license_id)
    reset_device(db, lic.id)
    return {"ok": True}


@router.delete("/keys/{license_id}")
async def delete_key(license_id: str, db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)):
    lic = _get_license_or_404(db, license_id)
    db.delete(lic)
    db.commit()
    return {"ok": True}


# ---------------- Devices ----------------

@router.get("/devices")
async def list_devices(
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    q = db.query(Device)
    if search:
        q = q.filter(Device.installation_id.ilike(f"%{search}%"))

    total = q.count()
    items = (
        q.order_by(Device.registered_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    results = []
    for d in items:
        row = d.to_dict()
        row["license_key"] = d.license.license_key if d.license else None
        results.append(row)

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size),
        "items": results,
    }


# ---------------- Logs ----------------

@router.get("/logs")
async def list_logs(
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
):
    q = db.query(Log)
    if status_filter and status_filter != "ALL":
        q = q.filter(Log.status == status_filter)

    total = q.count()
    items = (
        q.order_by(Log.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    results = []
    for l in items:
        row = l.to_dict()
        row["license_key"] = l.license.license_key if l.license else None
        results.append(row)

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size),
        "items": results,
    }


# ---------------- Settings ----------------

@router.post("/settings/change-password")
async def change_password(
    body: ChangePasswordRequest,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    if not verify_password(body.current_password, admin.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if len(body.new_password) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters")

    admin.password_hash = hash_password(body.new_password)
    db.commit()
    return {"ok": True}
