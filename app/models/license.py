import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, Enum, func
from sqlalchemy.orm import relationship

from app.database import Base


class LicenseStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    BANNED = "BANNED"
    EXPIRED = "EXPIRED"   # derived at read-time from expires_at, also settable manually


class License(Base):
    __tablename__ = "licenses"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    license_key = Column(String(64), unique=True, index=True, nullable=False)
    status = Column(Enum(LicenseStatus), default=LicenseStatus.ACTIVE, nullable=False)

    note = Column(String(255), nullable=True)          # optional admin label
    duration_label = Column(String(64), nullable=True)  # e.g. "30 Days", "Lifetime"

    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    activated_at = Column(DateTime, nullable=True)   # set on first successful device registration
    expires_at = Column(DateTime, nullable=True)     # null == lifetime

    devices = relationship("Device", back_populates="license", cascade="all, delete-orphan")
    logs = relationship("Log", back_populates="license", cascade="all, delete-orphan")

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    def to_dict(self):
        return {
            "id": self.id,
            "license_key": self.license_key,
            "status": self.status.value if isinstance(self.status, LicenseStatus) else self.status,
            "note": self.note,
            "duration_label": self.duration_label,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "activated_at": self.activated_at.isoformat() if self.activated_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_expired": self.is_expired(),
            "device_count": len(self.devices) if self.devices is not None else 0,
        }
