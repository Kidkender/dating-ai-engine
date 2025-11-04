from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from typing import cast

from .config import settings

engine = create_engine(cast(str, settings.DATABASE_URL))
SessionLocal = sessionmaker(bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection():
    """Check if database is reachable"""
    try:
        engine.connect()
        return True
    except:
        return False
