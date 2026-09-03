import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship

from app.database import Base


class Device(Base):
    __tablename__ = "devices"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    license_id = Column(String(36), ForeignKey("licenses.id"), nullable=False, index=True)
    installation_id = Column(String(255), nullable=False, index=True)
    app_version = Column(String(32), nullable=True)

    registered_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    last_login = Column(DateTime, nullable=True)

    license = relationship("License", back_populates="devices")

    def to_dict(self):
        return {
            "id": self.id,
            "license_id": self.license_id,
            "installation_id": self.installation_id,
            "app_version": self.app_version,
            "registered_at": self.registered_at.isoformat() if self.registered_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
        }
