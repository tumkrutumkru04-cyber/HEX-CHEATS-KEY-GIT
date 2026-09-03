import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, func

from app.database import Base


class AppSecret(Base):
    """
    Key-value store for secrets the app generates for itself (SECRET_KEY,
    PAYLOAD_ENCRYPTION_KEY) when they aren't supplied via environment
    variables. Storing them here instead of only in memory means they
    survive restarts/redeploys without you having to set anything in
    Railway - the app is fully self-provisioning.

    If you DO set SECRET_KEY / PAYLOAD_ENCRYPTION_KEY as environment
    variables, those always take priority over anything stored here.
    """
    __tablename__ = "app_secrets"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    key = Column(String(64), unique=True, index=True, nullable=False)
    value = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())
