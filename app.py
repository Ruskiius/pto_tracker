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

@app.route("/employees/new", methods=["GET", "POST"])
@login_required
def employee_new():
    if request.method == "POST":
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        employment_type = request.form.get("employment_type", "").strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip()

        errors = []
        if not first_name:
            errors.append("First name is required.")
        if not last_name:
            errors.append("Last name is required.")
        if employment_type not in ("hourly", "salaried"):
            errors.append("Employment type must be hourly or salaried.")

        if errors:
            return render_template(
                "employee_form.html",
                errors=errors,
                first_name=first_name,
                last_name=last_name,
                employment_type=employment_type,
                phone=phone,
                email=email,
            )

        conn = get_db_connection()
        # Insert employee
        cur = conn.execute(
            """
            INSERT INTO employees (first_name, last_name, employment_type, phone, email, status)
            VALUES (?, ?, ?, ?, ?, 'active')
            """,
            (first_name, last_name, employment_type, phone, email),
        )
        employee_id = cur.lastrowid

        # Fetch PTO types
        pto_types = conn.execute("SELECT id FROM pto_types").fetchall()

        # Create PTO balances with default 40 hours allotted for each type
        for pto_type in pto_types:
            conn.execute(
                """
                INSERT INTO pto_balances (employee_id, pto_type_id, hours_allotted, hours_used)
                VALUES (?, ?, ?, 0)
                """,
                (employee_id, pto_type["id"], 40.0),
            )

        conn.commit()
        conn.close()

        return redirect(url_for("employees_list"))

    # GET request: render empty form
    return render_template("employee_form.html")

@app.route("/employees/<int:employee_id>")
@login_required
def employee_detail(employee_id):
    conn = get_db_connection()

    # Get employee info
    employee = conn.execute(
        """
        SELECT id, first_name, last_name, employment_type, phone, email, status
        FROM employees
        WHERE id = ?
        """,
        (employee_id,),
    ).fetchone()

    if employee is None:
        conn.close()
        return "Employee not found", 404

    # Get PTO balances
    balances = conn.execute(
        """
        SELECT
            pt.display_name AS pto_name,
            pt.code AS pto_code,
            b.hours_allotted,
            b.hours_used,
            (b.hours_allotted - b.hours_used) AS hours_remaining
        FROM pto_balances b
        JOIN pto_types pt ON pt.id = b.pto_type_id
        WHERE b.employee_id = ?
        ORDER BY pt.display_name
        """,
        (employee_id,),
    ).fetchall()

    # Get PTO entries (history)
    pto_entries = conn.execute(
        """
        SELECT
            e.id,
            pt.display_name AS pto_name,
            e.start_date,
            e.end_date,
            e.hours,
            e.notes,
            m.full_name AS manager_name,
            e.created_at
        FROM pto_entries e
        JOIN pto_types pt ON pt.id = e.pto_type_id
        LEFT JOIN managers m ON m.id = e.created_by_manager_id
        WHERE e.employee_id = ?
        ORDER BY e.start_date DESC
        """,
        (employee_id,),
    ).fetchall()

    conn.close()

    return render_template(
        "employee_detail.html",
        employee=employee,
        balances=balances,
        pto_entries=pto_entries,
    )


if __name__ == "__main__":
    app.run(debug=True)


