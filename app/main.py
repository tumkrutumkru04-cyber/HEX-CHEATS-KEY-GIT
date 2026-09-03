import secrets as secrets_module
import logging

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import init_db, SessionLocal
from app.models.admin import Admin
from app.security.admin_auth import hash_password
from app.security.secrets_store import get_or_create_secret

from app.routes import auth_api, admin_pages, admin_auth_routes, admin_api

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("hexprotocol")

settings = get_settings()

app = FastAPI(
    title="HEX PROTOCOL",
    description="License key administration platform + secure verification API",
    version="1.0.0",
    docs_url="/api/docs" if settings.ENV != "production" else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # the API is called by a native Android client, not a browser
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)

app.mount("/admin/static", StaticFiles(directory="app/admin/static"), name="admin_static")

app.include_router(auth_api.router)
app.include_router(admin_auth_routes.router)
app.include_router(admin_pages.router)
app.include_router(admin_api.router)


def _resolve_secrets():
    """
    Fills in settings.SECRET_KEY and settings.PAYLOAD_ENCRYPTION_KEY.
    Priority: environment variable > value already stored in the
    database (from a previous boot) > freshly generated + saved to the
    database. This means these two values never need to be set by hand,
    but also never silently change between restarts.
    """
    db = SessionLocal()
    try:
        secret_key, source = get_or_create_secret(db, "SECRET_KEY", "SECRET_KEY")
        settings.SECRET_KEY = secret_key
        logger.info(f"SECRET_KEY resolved from: {source}")

        payload_key, source = get_or_create_secret(db, "PAYLOAD_ENCRYPTION_KEY", "PAYLOAD_ENCRYPTION_KEY")
        settings.PAYLOAD_ENCRYPTION_KEY = payload_key
        logger.info(f"PAYLOAD_ENCRYPTION_KEY resolved from: {source}")
    finally:
        db.close()


def _seed_default_admin():
    """
    Creates the first admin account if the admins table is empty.
    Uses ADMIN_USERNAME / ADMIN_PASSWORD env vars if you set them;
    otherwise auto-generates a username/password and prints them to
    the deploy logs ONCE. Copy them from the logs immediately after
    first deploy - they are not stored anywhere in plain text after
    this.
    """
    import os

    db = SessionLocal()
    try:
        if db.query(Admin).count() > 0:
            return

        username = os.getenv("ADMIN_USERNAME") or "admin"
        password = os.getenv("ADMIN_PASSWORD") or secrets_module.token_urlsafe(12)

        admin = Admin(username=username, password_hash=hash_password(password))
        db.add(admin)
        db.commit()

        if os.getenv("ADMIN_PASSWORD"):
            logger.info(f"Seeded admin account '{username}' from ADMIN_USERNAME/ADMIN_PASSWORD.")
        else:
            logger.info("=" * 60)
            logger.info("No ADMIN_USERNAME/ADMIN_PASSWORD set - generated one for you:")
            logger.info(f"  username: {username}")
            logger.info(f"  password: {password}")
            logger.info("Save this now - it will not be shown again. Change it from")
            logger.info("the Settings page after your first login.")
            logger.info("=" * 60)
    finally:
        db.close()


@app.on_event("startup")
async def on_startup():
    init_db()
    _resolve_secrets()
    _seed_default_admin()


@app.get("/")
async def root():
    return {"service": "HEX PROTOCOL", "status": "online"}


@app.get("/health")
async def health():
    return {"status": "ok"}
