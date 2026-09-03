import json
import time
from collections import defaultdict, deque

from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_client_ip
from app.config import get_settings
from app.security.crypto_manager import encrypt_data, decrypt_data, DecryptionError
from app.services.device_service import verify_and_register

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
settings = get_settings()

# Very small in-memory sliding-window rate limiter, keyed by IP.
# Fine for a single Railway instance; swap for Redis if you scale to
# multiple instances.
_request_log: dict[str, deque] = defaultdict(deque)


def _rate_limited(ip: str) -> bool:
    now = time.time()
    window = 60.0
    q = _request_log[ip]
    while q and now - q[0] > window:
        q.popleft()
    if len(q) >= settings.RATE_LIMIT_PER_MINUTE:
        return True
    q.append(now)
    return False


def _build_response(status_code: str, message: str, expires_at, use_encryption: bool) -> dict:
    body = {
        "status": status_code,
        "message": message,
        "expires_at": expires_at,
    }
    if not use_encryption:
        return body
    encrypted = encrypt_data(json.dumps(body), settings.PAYLOAD_ENCRYPTION_KEY)
    return {"payload": encrypted}


@router.post("/verify")
async def verify_license(request: Request, db: Session = Depends(get_db)):
    """
    Accepts either:
      - {"payload": "<base64url AES-256-GCM blob>"}   when encryption is enabled (default)
      - {"license_key": "...", "installation_id": "...", "app_version": "..."}  when
        ENCRYPTION_ENABLED=false (useful for local testing only - do not
        disable encryption in production).

    Always returns an equivalently-shaped response (encrypted envelope
    or plain JSON) matching the request mode.
    """
    ip = get_client_ip(request)
    if _rate_limited(ip):
        raise HTTPException(status_code=429, detail="Too many requests")

    try:
        raw_body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    use_encryption = settings.ENCRYPTION_ENABLED

    if use_encryption:
        payload_b64 = raw_body.get("payload")
        if not payload_b64:
            raise HTTPException(status_code=400, detail="Missing 'payload' field")
        try:
            decrypted_json = decrypt_data(payload_b64, settings.PAYLOAD_ENCRYPTION_KEY)
            data = json.loads(decrypted_json)
        except (DecryptionError, json.JSONDecodeError):
            # Deliberately vague - don't leak why decryption failed
            raise HTTPException(status_code=400, detail="Unable to process request")
    else:
        data = raw_body

    license_key = (data.get("license_key") or "").strip()
    installation_id = (data.get("installation_id") or "").strip()
    app_version = data.get("app_version")

    if not license_key or not installation_id:
        body = _build_response("INVALID_KEY", "license_key and installation_id are required.", None, use_encryption)
        return body

    try:
        status_code, message, lic = verify_and_register(
            db=db,
            license_key=license_key,
            installation_id=installation_id,
            app_version=app_version,
            source_ip=ip,
        )
    except Exception:
        db.rollback()
        return _build_response("SERVER_ERROR", "An internal error occurred.", None, use_encryption)

    expires_at = None
    if lic is not None and lic.expires_at is not None:
        expires_at = lic.expires_at.isoformat()

    return _build_response(status_code, message, expires_at, use_encryption)
