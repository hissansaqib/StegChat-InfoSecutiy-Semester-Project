from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, scoped_session
from ..core.config import Settings

settings = Settings()

# Enable SQLite WAL mode, busy timeout, and foreign keys on connect
connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False, "timeout": 30.0}

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    future=True,
    echo=False,
)

if settings.database_url.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.close()

SessionLocal = scoped_session(sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True))

def get_db():
    """FastAPI dependency that provides a DB session and ensures cleanup."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


