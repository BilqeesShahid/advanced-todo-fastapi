"""Database configuration for Phase II Todo Application."""
from typing import Generator
from sqlmodel import create_engine, Session
import os
from dotenv import load_dotenv
from sqlalchemy import event
from sqlalchemy.engine import Engine
import json

# Load environment variables but prioritize local development
load_dotenv()

# Use the DATABASE_URL from environment variable, with fallback to SQLite for local dev
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./todo_app_fallback.db")

# Check if we're using PostgreSQL or SQLite
if DATABASE_URL.startswith("postgresql"):
    print("[DB CONFIG] Using PostgreSQL database")
else:
    print(f"[DB CONFIG] Using SQLite database: {DATABASE_URL}")

# Create SQLModel engine
# For SQLite, we need to disable pool_pre_ping which is PostgreSQL-specific
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

# For SQLite, we need to handle PostgreSQL-specific types like ARRAY
if DATABASE_URL.startswith("sqlite"):
    # Import here to avoid issues when not using SQLite
    from sqlalchemy import text
    
    # Create engine first
    engine = create_engine(DATABASE_URL, echo=False, connect_args=connect_args)
    
    # Add event listener to handle array-like data for SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        # Enable foreign keys and WAL mode for better concurrency
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()
else:
    engine = create_engine(DATABASE_URL, echo=False, connect_args=connect_args)


def get_session() -> Generator[Session, None, None]:
    """Dependency for getting database sessions."""
    with Session(engine) as session:
        yield session
