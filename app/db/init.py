"""Initialize database tables."""
from sqlmodel import SQLModel
from app.models.user import User
from app.models.task import Task
from app.models.conversation import Conversation
from app.models.message import Message
from app.db.config import engine
import os


def init_db():
    """Create all tables in the database."""
    # Check if we're using SQLite and if it's the development database
    db_url = os.environ.get("DATABASE_URL", "")
    if "todo_app_dev.db" in db_url or db_url.startswith("sqlite"):
        print("[DB INIT] Dropping and recreating tables for development...")
        # For development, we might want to drop and recreate tables to ensure clean state
        SQLModel.metadata.drop_all(engine)
    
    print("[DB INIT] Creating all tables...")
    SQLModel.metadata.create_all(engine)
    print("[DB INIT] Tables created successfully.")


if __name__ == "__main__":
    init_db()
    print("Database tables created successfully.")
