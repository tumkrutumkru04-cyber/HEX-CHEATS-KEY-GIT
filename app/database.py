"""
SQLAlchemy engine / session management - auto-connecting with a
diagnostic log line and a SQLite fallback if DATABASE_URL is missing
or unreachable, so a misconfigured database never causes a silent
failure or a cryptic import-time crash.
"""
import sys

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import get_settings

settings = get_settings()

DATABASE_URL = settings.DATABASE_URL

if not DATABASE_URL:
    print("WARNING: DATABASE_URL environment variable not set.", file=sys.stderr)
    print("   Add a PostgreSQL database in Railway (+ New -> Database -> PostgreSQL) and redeploy.", file=sys.stderr)
    DATABASE_URL = "sqlite:///./hex_dev.db"
    print("WARNING: Using local SQLite fallback - data will NOT persist across Railway deploys!", file=sys.stderr)

# Railway sometimes provides "postgres://" - SQLAlchemy 2.x needs "postgresql://"
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

print(f"Connecting to database: {DATABASE_URL[:40]}...")
try:
    engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print("Database connection successful.")
except Exception as exc:
    print(f"ERROR: Database connection failed: {exc}", file=sys.stderr)
    sys.exit(1)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables. For a production project you'd typically use
    Alembic migrations instead, but this keeps first deploy to Railway
    simple - it's called once on startup in main.py."""
    from app.models import license, device, log, admin, app_secret  # noqa: F401
    Base.metadata.create_all(bind=engine)
