import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship

from app.database import Base


class Log(Base):
    __tablename__ = "logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    license_id = Column(String(36), ForeignKey("licenses.id"), nullable=True, index=True)
    installation_id = Column(String(255), nullable=True)
    source_ip = Column(String(64), nullable=True)
    status = Column(String(32), nullable=False)  # SUCCESS / INVALID_KEY / EXPIRED / DEVICE_MISMATCH / BANNED / SERVER_ERROR
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())

    license = relationship("License", back_populates="logs")

    def to_dict(self):
        return {
            "id": self.id,
            "license_id": self.license_id,
            "installation_id": self.installation_id,
            "source_ip": self.source_ip,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
