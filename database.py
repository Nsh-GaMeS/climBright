import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


def _resolve_db_path() -> Path:
    """Locate and ensure the SQLite directory exists before connecting."""
    base_dir = Path(__file__).resolve().parent
    config_dir = Path(os.environ.get("CLIMB_DB_DIR", base_dir / "db"))
    db_path = config_dir / "sqlite" / "users.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return db_path


DB_PATH = _resolve_db_path()
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH.as_posix()}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()