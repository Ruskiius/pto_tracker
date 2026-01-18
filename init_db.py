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
    conn.execute("PRAGMA foreign_keys = ON;")

    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    conn.executescript(schema_sql)

    # Seed roles
    print("Inserting roles...")
    roles = [
        ("admin", 1),
        ("manager", 1),
    ]
    conn.executemany(
        "INSERT OR IGNORE INTO roles (name, is_system) VALUES (?, ?)",
        roles,
    )

    # Seed permissions
    print("Inserting permissions...")
    permissions = [
        ("employees:remove_restore", "Soft-delete or restore employees"),
        ("employees:delete_permanent", "Permanently delete employees"),
        ("pto_types:manage", "Manage PTO types (create, edit, delete)"),
        ("balances:edit", "Edit PTO balances for employees"),
        ("managers:manage", "Manage manager accounts"),
    ]
    conn.executemany(
        "INSERT OR IGNORE INTO permissions (code, description) VALUES (?, ?)",
        permissions,
    )

    # Get role IDs
    admin_role = conn.execute("SELECT id FROM roles WHERE name = 'admin'").fetchone()
    manager_role = conn.execute("SELECT id FROM roles WHERE name = 'manager'").fetchone()

    if admin_role and manager_role:
        admin_role_id = admin_role[0]
        manager_role_id = manager_role[0]

        # Get permission IDs
        perm_map = {}
        for code, _ in permissions:
            perm = conn.execute("SELECT id FROM permissions WHERE code = ?", (code,)).fetchone()
            if perm:
                perm_map[code] = perm[0]

        # Assign all permissions to admin
        print("Assigning permissions to admin role...")
        admin_perms = [
            (admin_role_id, perm_map["employees:remove_restore"]),
            (admin_role_id, perm_map["employees:delete_permanent"]),
            (admin_role_id, perm_map["pto_types:manage"]),
            (admin_role_id, perm_map["balances:edit"]),
            (admin_role_id, perm_map["managers:manage"]),
        ]
        conn.executemany(
            "INSERT OR IGNORE INTO role_permissions (role_id, permission_id) VALUES (?, ?)",
            admin_perms,
        )

        # Assign limited permissions to manager (only what admin_or_manager_required currently allows)
        print("Assigning permissions to manager role...")
        manager_perms = [
            (manager_role_id, perm_map["employees:remove_restore"]),
            (manager_role_id, perm_map["balances:edit"]),
        ]
        conn.executemany(
            "INSERT OR IGNORE INTO role_permissions (role_id, permission_id) VALUES (?, ?)",
            manager_perms,
        )

    # Seed PTO types
    print("Inserting PTO types...")
    pto_types = [
        ("PERSONAL", "Personal Time", 1, 40),
        ("SICK", "Sick Time", 1, 40),
        ("VACATION", "Vacation Time", 1, 40),
    ]
    conn.executemany(
        "INSERT INTO pto_types (code, display_name, is_active, default_hours) VALUES (?, ?, ?, ?)",
        pto_types,
    )

    # Seed an admin manager
    print("Inserting admin user...")
    admin_username = "admin"
    admin_password = "password"  # you can change this after first login
    admin_full_name = "Admin User"
    admin_role = "admin"

    password_hash = generate_password_hash(admin_password, method="pbkdf2:sha256")

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
