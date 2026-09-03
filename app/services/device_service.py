from datetime import datetime
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from app.models.license import License, LicenseStatus
from app.models.device import Device
from app.models.log import Log
from app.services.license_service import effective_status


def verify_and_register(
    db: Session,
    license_key: str,
    installation_id: str,
    app_version: Optional[str],
    source_ip: Optional[str],
) -> Tuple[str, str, Optional[License]]:
    """
    Core verification flow shared by the /auth/verify endpoint.

    Returns (status_code, message, license_or_none) where status_code is
    one of: SUCCESS, INVALID_KEY, EXPIRED, DEVICE_MISMATCH, BANNED.

    Also writes a Log row for every attempt.
    """
    lic = db.query(License).filter(License.license_key == license_key).first()

    if lic is None:
        _write_log(db, None, installation_id, source_ip, "INVALID_KEY")
        return "INVALID_KEY", "License key does not exist.", None

    status = effective_status(lic)

    if status == LicenseStatus.BANNED.value:
        _write_log(db, lic.id, installation_id, source_ip, "BANNED")
        return "BANNED", "This license key has been banned.", lic

    if status == LicenseStatus.INACTIVE.value:
        _write_log(db, lic.id, installation_id, source_ip, "INVALID_KEY")
        return "INVALID_KEY", "This license key is not active.", lic

    if status == LicenseStatus.EXPIRED.value:
        _write_log(db, lic.id, installation_id, source_ip, "EXPIRED")
        return "EXPIRED", "This license key has expired.", lic

    # ACTIVE from here on - check device binding
    existing_device = db.query(Device).filter(Device.license_id == lic.id).first()

    if existing_device is None:
        # First-ever successful use -> auto-register this installation id
        new_device = Device(
            license_id=lic.id,
            installation_id=installation_id,
            app_version=app_version,
            last_login=datetime.utcnow(),
        )
        db.add(new_device)
        if lic.activated_at is None:
            lic.activated_at = datetime.utcnow()
        db.commit()
        _write_log(db, lic.id, installation_id, source_ip, "SUCCESS")
        return "SUCCESS", "License verified and device registered.", lic

    if existing_device.installation_id != installation_id:
        _write_log(db, lic.id, installation_id, source_ip, "DEVICE_MISMATCH")
        return "DEVICE_MISMATCH", "This license is already bound to a different device.", lic

    # Same device -> success, update last_login/app_version
    existing_device.last_login = datetime.utcnow()
    if app_version:
        existing_device.app_version = app_version
    db.commit()
    _write_log(db, lic.id, installation_id, source_ip, "SUCCESS")
    return "SUCCESS", "License verified.", lic


def reset_device(db: Session, license_id: str) -> bool:
    deleted = db.query(Device).filter(Device.license_id == license_id).delete()
    db.commit()
    return deleted > 0


def _write_log(db: Session, license_id: Optional[str], installation_id: Optional[str], source_ip: Optional[str], status: str):
    log = Log(
        license_id=license_id,
        installation_id=installation_id,
        source_ip=source_ip,
        status=status,
    )
    db.add(log)
    db.commit()
