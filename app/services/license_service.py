import secrets
import string
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.models.license import License, LicenseStatus

ALPHABET = string.ascii_uppercase + string.digits


def _random_block(length: int = 4) -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(length))


def generate_key_string(prefix: str = "HEX") -> str:
    """Format: PREFIX-XXXX-XXXX-XXXX"""
    prefix = (prefix or "HEX").strip().upper()[:16]
    return f"{prefix}-{_random_block()}-{_random_block()}-{_random_block()}"


def resolve_duration(
    duration_type: str,
    custom_hours: Optional[int] = None,
    custom_days: Optional[int] = None,
) -> Optional[timedelta]:
    """Returns a timedelta for the given duration type, or None for lifetime."""
    mapping = {
        "1_hour": timedelta(hours=1),
        "1_day": timedelta(days=1),
        "7_days": timedelta(days=7),
        "30_days": timedelta(days=30),
    }
    if duration_type in mapping:
        return mapping[duration_type]
    if duration_type == "custom_hours":
        if not custom_hours or custom_hours <= 0:
            raise ValueError("custom_hours must be a positive integer")
        return timedelta(hours=custom_hours)
    if duration_type == "custom_days":
        if not custom_days or custom_days <= 0:
            raise ValueError("custom_days must be a positive integer")
        return timedelta(days=custom_days)
    if duration_type == "lifetime":
        return None
    raise ValueError(f"Unknown duration_type: {duration_type}")


def duration_label(duration_type: str, custom_hours=None, custom_days=None) -> str:
    labels = {
        "1_hour": "1 Hour",
        "1_day": "1 Day",
        "7_days": "7 Days",
        "30_days": "30 Days",
        "lifetime": "Lifetime",
    }
    if duration_type == "custom_hours":
        return f"{custom_hours} Hour(s)"
    if duration_type == "custom_days":
        return f"{custom_days} Day(s)"
    return labels.get(duration_type, duration_type)


def create_licenses(
    db: Session,
    quantity: int,
    prefix: str,
    duration_type: str,
    custom_hours: Optional[int] = None,
    custom_days: Optional[int] = None,
    note: Optional[str] = None,
) -> list[License]:
    delta = resolve_duration(duration_type, custom_hours, custom_days)
    label = duration_label(duration_type, custom_hours, custom_days)

    created = []
    for _ in range(quantity):
        # Ensure uniqueness even under (unlikely) collision
        for _attempt in range(5):
            key_str = generate_key_string(prefix)
            exists = db.query(License).filter(License.license_key == key_str).first()
            if not exists:
                break
        else:
            raise RuntimeError("Failed to generate a unique license key after 5 attempts")

        lic = License(
            license_key=key_str,
            status=LicenseStatus.ACTIVE,
            note=note,
            duration_label=label,
            expires_at=None,  # only set once the key is first activated (on device registration)
        )
        # Store the resolved duration on the instance temporarily so the
        # route layer can persist "pending duration" if you want
        # expiry to start counting from generation instead of activation.
        # Default behavior here: expiry starts counting from GENERATION time.
        if delta is not None:
            lic.expires_at = datetime.utcnow() + delta

        db.add(lic)
        created.append(lic)

    db.commit()
    for lic in created:
        db.refresh(lic)
    return created


def effective_status(lic: License) -> str:
    """Computes the status the way an admin/API consumer should see it,
    treating a past expires_at as EXPIRED even if the stored status
    field still says ACTIVE."""
    if lic.status == LicenseStatus.BANNED:
        return LicenseStatus.BANNED.value
    if lic.status == LicenseStatus.INACTIVE:
        return LicenseStatus.INACTIVE.value
    if lic.is_expired():
        return LicenseStatus.EXPIRED.value
    return LicenseStatus.ACTIVE.value
