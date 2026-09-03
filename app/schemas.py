from typing import Optional
from pydantic import BaseModel, Field


# ---------- Public API (encrypted envelope) ----------

class EncryptedEnvelope(BaseModel):
    """The wire shape POSTed to /api/v1/auth/verify when encryption is enabled."""
    payload: str = Field(..., description="base64url AES-256-GCM encrypted JSON payload")


class VerifyRequest(BaseModel):
    """Decrypted shape of the payload the Java client sends."""
    license_key: str
    installation_id: str
    app_version: Optional[str] = None


class VerifyResult(BaseModel):
    status: str  # SUCCESS / INVALID_KEY / EXPIRED / DEVICE_MISMATCH / BANNED / SERVER_ERROR
    message: str
    expires_at: Optional[str] = None


# ---------- Admin key generation ----------

class GenerateKeysRequest(BaseModel):
    quantity: int = Field(1, ge=1, le=500)
    prefix: str = Field("HEX", min_length=1, max_length=16)
    duration_type: str = Field(..., description="1_hour | custom_hours | 1_day | custom_days | 7_days | 30_days | lifetime")
    custom_hours: Optional[int] = Field(None, ge=1)
    custom_days: Optional[int] = Field(None, ge=1)
    note: Optional[str] = None


class KeyActionRequest(BaseModel):
    license_id: str


class ExtendExpiryRequest(BaseModel):
    license_id: str
    additional_hours: Optional[int] = None
    additional_days: Optional[int] = None
