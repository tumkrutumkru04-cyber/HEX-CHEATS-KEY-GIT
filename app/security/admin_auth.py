"""
Admin panel authentication: password hashing (bcrypt via passlib) and a
signed, expiring session token (itsdangerous) stored in an httponly
cookie. This is separate from the AES-256-GCM application-layer
encryption used for the Java client API - the admin dashboard is a
normal server-rendered site protected by HTTPS + a session cookie.
"""
from datetime import datetime, timedelta
from typing import Optional

from passlib.context import CryptContext
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

from app.config import get_settings

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

COOKIE_NAME = "hex_admin_session"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.SECRET_KEY, salt="hex-admin-session")


def create_session_token(admin_id: str, username: str) -> str:
    return _serializer().dumps({"admin_id": admin_id, "username": username})


def read_session_token(token: str) -> Optional[dict]:
    try:
        data = _serializer().loads(token, max_age=settings.SESSION_MAX_AGE_SECONDS)
        return data
    except (BadSignature, SignatureExpired):
        return None
