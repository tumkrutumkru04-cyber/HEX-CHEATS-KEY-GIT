"""
Application configuration.

SECRET_KEY and PAYLOAD_ENCRYPTION_KEY are optional here on purpose: if
you don't set them as environment variables, the app generates them
itself on first boot and stores them in the database (see
security/secrets_store.py + main.py startup), so you never have to
paste a generated key into Railway. If you DO set them as env vars,
those are used instead and take priority.
"""
import os
from functools import lru_cache


class Settings:
    # --- Core ---
    APP_NAME: str = "HEX PROTOCOL"

    def __init__(self):
        self.ENV: str = os.getenv("ENV", "production")
        self.DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

        # --- Database ---
        # Railway injects DATABASE_URL automatically when a PostgreSQL
        # plugin is attached. Falls back to local SQLite only if it's
        # genuinely missing (see database.py for the connection log).
        self.DATABASE_URL: str = os.getenv("DATABASE_URL", "")

        # --- Admin session security ---
        # Resolved at startup (see main.py) - env var if set, otherwise
        # a DB-persisted auto-generated value. Left blank here.
        self.SECRET_KEY: str = os.getenv("SECRET_KEY", "")
        self.SESSION_MAX_AGE_SECONDS: int = int(os.getenv("SESSION_MAX_AGE_SECONDS", "28800"))  # 8h

        # --- Application-layer payload encryption (AES-256-GCM) ---
        # Same resolution pattern as SECRET_KEY - see main.py startup.
        self.PAYLOAD_ENCRYPTION_KEY: str = os.getenv("PAYLOAD_ENCRYPTION_KEY", "")
        self.ENCRYPTION_ENABLED: bool = os.getenv("ENCRYPTION_ENABLED", "true").lower() == "true"

        # --- Rate limiting ---
        self.RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "30"))

        # --- Key generation ---
        self.DEFAULT_KEY_PREFIX: str = os.getenv("DEFAULT_KEY_PREFIX", "HEX")


@lru_cache
def get_settings() -> Settings:
    return Settings()
