from flask import Flask, render_template, redirect, url_for, request, session
from werkzeug.security import check_password_hash
import sqlite3

from functools import wraps

from pathlib import Path

app = Flask(__name__)
app.secret_key = "CHANGE_THIS_TO_SOMETHING_RANDOM_LATER"

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "pto_tracker.db"


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # access columns by name
    return conn


app = Flask(__name__)
app.secret_key = "CHANGE_THIS_TO_SOMETHING_RANDOM_LATER"  # required for sessions


# --- Authentication helpers ---
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper



# --- Routes ---
@app.route("/")
def home():
    return redirect(url_for("dashboard"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        conn = get_db_connection()
        cur = conn.execute(
            "SELECT id, username, password_hash, full_name, role FROM managers WHERE username = ?",
            (username,),
        )
        user = cur.fetchone()
        conn.close()

        if user is None or not check_password_hash(user["password_hash"], password):
            return render_template("login.html", error="Invalid username or password")

        # Login success
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        session["full_name"] = user["full_name"]
        session["role"] = user["role"]

        return redirect(url_for("dashboard"))

    return render_template("login.html")



@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    return render_template(
        "dashboard.html",
        username=session.get("username"),
        full_name=session.get("full_name"),
        role=session.get("role"),
    )
@app.route("/employees")
@login_required
def employees_list():
    conn = get_db_connection()
    employees = conn.execute(
        """
        SELECT id, first_name, last_name, employment_type, phone, email, status
        FROM employees
        WHERE status = 'active'
        ORDER BY last_name, first_name
        """
    ).fetchall()
    conn.close()

    return render_template("employees_list.html", employees=employees)




if __name__ == "__main__":
    app.run(debug=True)
