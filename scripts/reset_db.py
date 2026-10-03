"""
Database reset utility for SchemaFlow.
Drops and recreates all SQLModel tables for a clean slate.
"""
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.database import engine, create_db_and_tables
from sqlmodel import SQLModel


def reset_database() -> None:
    print("[*] Resetting SchemaFlow database...")
    SQLModel.metadata.drop_all(engine)
    create_db_and_tables()
    print("[OK] Database reset completed successfully.")


if __name__ == "__main__":
    reset_database()
