"""
Resolves a secret's value with this priority:
  1. Environment variable (if you explicitly set one, it always wins)
  2. Previously auto-generated value stored in the app_secrets table
  3. Freshly generated value, which is then saved to app_secrets so it
     stays stable on every future boot

This is what lets the app run with zero required secret env vars while
still never silently rotating a key out from under you.
"""
import os
import secrets as secrets_module

from sqlalchemy.orm import Session

from app.models.app_secret import AppSecret


def get_or_create_secret(db: Session, env_var_name: str, db_key: str, length: int = 32) -> tuple[str, str]:
    """
    Returns (value, source) where source is "env", "database", or "generated".
    """
    env_value = os.getenv(env_var_name)
    if env_value:
        return env_value, "env"

    existing = db.query(AppSecret).filter(AppSecret.key == db_key).first()
    if existing:
        return existing.value, "database"

    new_value = secrets_module.token_urlsafe(length)
    db.add(AppSecret(key=db_key, value=new_value))
    db.commit()
    return new_value, "generated"
