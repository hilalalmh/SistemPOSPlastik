from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


def _engine_options(url: str) -> dict:
    options: dict = {"pool_pre_ping": True, "future": True}
    if url.startswith(("mysql", "mariadb")):
        # Keep MySQL connections in UTC and recycle before typical wait_timeout
        # so shared hosting (cPanel) does not drop idle connections.
        options["connect_args"] = {
            "charset": "utf8mb4",
            "init_command": "SET time_zone = '+00:00'",
        }
        options["pool_recycle"] = 280
    return options


engine = create_engine(settings.database_url, **_engine_options(settings.database_url))

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
