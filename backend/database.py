import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/training")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


def init_db():
    """Create database tables if they do not already exist."""
    # Import models for side effects so SQLAlchemy is aware of them
    from . import models  # noqa: F401

    Base.metadata.create_all(bind=engine)

def get_session():
    """Yield a SQLAlchemy session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
