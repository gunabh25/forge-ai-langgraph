"""
Database configuration for the POS system.

This module sets up the SQLAlchemy engine, session factory, and declarative base
for interacting with the PostgreSQL database. It also provides a dependency
function `get_db` for managing database sessions within FastAPI routes.
"""

from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.engine import URL

from app.config.settings import settings

# Construct the database URL from settings
# Example: postgresql://user:password@host:port/dbname
SQLALCHEMY_DATABASE_URL: URL = settings.DATABASE_URL

# Create the SQLAlchemy engine
# pool_pre_ping=True ensures that connections are alive before being used
# pool_size and max_overflow are configured for connection pooling,
# which is beneficial for performance and resource management.
# These values can be tuned based on application load and PgBouncer configuration.
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    connect_args={
        "application_name": settings.APP_NAME
    }
)

# Create a SessionLocal class
# This class will be an actual database session.
# Each instance of SessionLocal will be a database session.
# The `autocommit=False` means that the session will not commit changes automatically.
# The `autoflush=False` means that the session will not flush changes to the database automatically.
# The `bind=engine` connects the session to our database engine.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create a declarative base
# This Base class will be inherited by our SQLAlchemy models.
# It allows us to define database tables as Python classes.
Base = declarative_base()


def get_db() -> Generator:
    """
    Dependency function to provide a database session.

    This function yields a database session, ensuring that the session is
    properly closed after the request is processed, even if errors occur.
    It's designed to be used with FastAPI's dependency injection system.

    Yields:
        Session: A SQLAlchemy database session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()