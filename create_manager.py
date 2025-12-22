import sqlite3
from werkzeug.security import generate_password_hash

DB_PATH = "pto_tracker.db"

username = "manager1"
password = "password"  # change if you want
full_name = "Manager One"
role = "manager"  # important

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute(
    """
    INSERT INTO managers (username, password_hash, full_name, role)
    VALUES (?, ?, ?, ?)
    """,
    (username, generate_password_hash(password), full_name, role),
)

conn.commit()
conn.close()

print(f"Created user: {username} with role={role}")
