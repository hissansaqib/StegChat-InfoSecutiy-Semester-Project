from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from ..core.config import Settings

settings = Settings()
engine = create_engine(settings.database_url, future=True, echo=False)
SessionLocal = scoped_session(sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True))

def get_db():
    """FastAPI dependency that provides a DB session and ensures cleanup."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

