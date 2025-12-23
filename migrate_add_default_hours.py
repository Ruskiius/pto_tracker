#!/usr/bin/env python3
"""
Migration script to add default_hours column to pto_types table.
Run this on existing databases to add the new column.
"""
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "pto_tracker.db"


def migrate():
    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    
    # Check if column already exists
    cursor = conn.execute("PRAGMA table_info(pto_types);")
    columns = [row[1] for row in cursor.fetchall()]
    
    if "default_hours" in columns:
        print("Column 'default_hours' already exists in pto_types table.")
        conn.close()
        return
    
    print("Adding default_hours column to pto_types table...")
    try:
        conn.execute("ALTER TABLE pto_types ADD COLUMN default_hours REAL NOT NULL DEFAULT 40;")
        conn.commit()
        print("Migration successful! Column 'default_hours' added with default value of 40.")
    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
