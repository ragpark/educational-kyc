from __future__ import annotations

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .models import mapper_registry

DATABASE_URL = os.getenv("DATABASE_URL", ${{ Postgres.DATABASE_URL }})
engine = create_engine(DATABASE_URL, echo=False)

SessionLocal = sessionmaker(bind=engine)


def init_db() -> None:
    """Create tables based on mapped dataclasses."""
    mapper_registry.metadata.create_all(engine)
