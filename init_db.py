import sqlite3
from pathlib import Path
from werkzeug.security import generate_password_hash

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "pto_tracker.db"
SCHEMA_PATH = BASE_DIR / "schema.sql"


def init_db():
    # Remove existing DB during development if you want a clean slate
    if DB_PATH.exists():
        print(f"Deleting existing database at {DB_PATH}")
        DB_PATH.unlink()

    print(f"Creating new database at {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)

    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    conn.executescript(schema_sql)

    # Seed PTO types
    print("Inserting PTO types...")
    pto_types = [
        ("PERSONAL", "Personal Time"),
        ("SICK", "Sick Time"),
        ("VACATION", "Vacation Time"),
    ]
    conn.executemany(
        "INSERT INTO pto_types (code, display_name) VALUES (?, ?)",
        pto_types,
    )

    # Seed an admin manager
    print("Inserting admin user...")
    admin_username = "admin"
    admin_password = "password"  # you can change this after first login
    admin_full_name = "Admin User"
    admin_role = "admin"

    password_hash = generate_password_hash(admin_password)

    conn.execute(
        """
        INSERT INTO managers (username, password_hash, full_name, role)
        VALUES (?, ?, ?, ?)
        """,
        (admin_username, password_hash, admin_full_name, admin_role),
    )

    conn.commit()
    conn.close()
    print("Database initialized successfully.")


if __name__ == "__main__":
    init_db()
