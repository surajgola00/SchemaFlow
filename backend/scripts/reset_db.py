"""
reset_db.py — safely drops and recreates the SchemaFlow SQLite database.

Usage (from backend/ directory):
    python scripts/reset_db.py
    python scripts/reset_db.py --yes   # skip confirmation prompt
"""
from __future__ import annotations

import argparse
import os
import sys

# Ensure the app package is importable when run from backend/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def main() -> None:
    parser = argparse.ArgumentParser(description="Reset SchemaFlow database")
    parser.add_argument("--yes", action="store_true", help="Skip confirmation")
    args = parser.parse_args()

    from app.config import get_settings

    settings = get_settings()
    db_url = settings.database_url

    # Extract file path from sqlite URL
    if db_url.startswith("sqlite:///"):
        db_path = db_url[len("sqlite:///"):]
        if not os.path.isabs(db_path):
            db_path = os.path.join(
                os.path.dirname(__file__), "..", db_path
            )
        db_path = os.path.normpath(db_path)
    else:
        print(f"Non-SQLite database URL: {db_url}. Manual reset required.")
        sys.exit(1)

    if not args.yes:
        answer = input(
            f"⚠️  This will DELETE {db_path} and recreate an empty database.\n"
            "   Type 'yes' to continue: "
        )
        if answer.strip().lower() != "yes":
            print("Aborted.")
            sys.exit(0)

    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"[OK] Deleted {db_path}")
    else:
        print(f"[INFO] {db_path} did not exist - creating fresh.")

    from app.database import create_db_and_tables

    create_db_and_tables()
    print("[OK] Database recreated with all tables.")


if __name__ == "__main__":
    main()
