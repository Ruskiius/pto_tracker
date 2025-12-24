from flask import (
    Flask,
    render_template,
    redirect,
    url_for,
    request,
    session,
    abort,
    flash,
)
from werkzeug.security import check_password_hash
import sqlite3
import re
from datetime import date, datetime
import calendar as cal


from functools import wraps

from pathlib import Path




BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "pto_tracker.db"


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
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

def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        if session.get("role") != "admin":
            flash("Admin access required.", "error")
            return redirect(url_for("dashboard"))
        return f(*args, **kwargs)
    return wrapper

def admin_or_manager_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        if session.get("role") not in ("admin", "manager"):
            flash("Access denied.", "error")
            return redirect(url_for("dashboard"))
        return f(*args, **kwargs)
    return wrapper


def ensure_default_pto_types(conn):
    """Ensure the default PTO types exist in the database."""

    existing_count = conn.execute("SELECT COUNT(*) FROM pto_types").fetchone()[0]

    if existing_count == 0:
        default_types = [
            ("PERSONAL", "Personal Time", 1, 40),
            ("SICK", "Sick Time", 1, 40),
            ("VACATION", "Vacation Time", 1, 40),
        ]
        conn.executemany(
            "INSERT OR IGNORE INTO pto_types (code, display_name, is_active, default_hours) VALUES (?, ?, ?, ?)",
            default_types,
        )
        conn.commit()


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

        # Fetch active PTO types
        pto_types = conn.execute(
            "SELECT id, default_hours FROM pto_types WHERE is_active = 1"
        ).fetchall()

        # Create PTO balances using default_hours from each PTO type
        for pto_type in pto_types:
            conn.execute(
                """
                INSERT INTO pto_balances (employee_id, pto_type_id, hours_allotted, hours_used)
                VALUES (?, ?, ?, 0)
                """,
                (employee_id, pto_type["id"], pto_type["default_hours"]),
            )

        conn.commit()
        conn.close()

        return redirect(url_for("employees_list"))

    # GET request: render empty form
    return render_template("employee_form.html")

@app.route("/employees/<int:employee_id>", methods=["GET", "POST"])
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

    is_admin = session.get("role") == "admin"
    errors = []
    form_data = None

    pto_rows = conn.execute(
        """
        SELECT
            pt.id AS pto_type_id,
            pt.display_name,
            b.hours_allotted,
            b.hours_used
        FROM pto_types pt
        LEFT JOIN pto_balances b
            ON b.pto_type_id = pt.id AND b.employee_id = ?
        WHERE pt.is_active = 1
        ORDER BY pt.display_name
        """,
        (employee_id,),
    ).fetchall()

    if request.method == "POST":
        if not is_admin:
            conn.close()
            flash("Admin access required to update balances.", "error")
            return redirect(url_for("employee_detail", employee_id=employee_id))

        form_data = request.form

        if not pto_rows:
            errors.append("No active PTO types available to update.")
        else:
            updates = []
            for row in pto_rows:
                field_name = str(row["pto_type_id"])
                raw_value = form_data.get(field_name, "").strip()
                hours_used = row["hours_used"] if row["hours_used"] is not None else 0.0
                row_has_error = False

                if raw_value == "":
                    errors.append(f"Hours allotted for {row['display_name']} are required.")
                    row_has_error = True
                else:
                    try:
                        new_hours_allotted = float(raw_value)
                        if new_hours_allotted < 0:
                            errors.append(
                                f"Hours allotted for {row['display_name']} must be greater than or equal to 0."
                            )
                            row_has_error = True
                    except ValueError:
                        errors.append(
                            f"Hours allotted for {row['display_name']} must be a valid number."
                        )
                        row_has_error = True

                if row_has_error:
                    continue

                if new_hours_allotted < hours_used:
                    errors.append(
                        f"Hours allotted for {row['display_name']} cannot be less than hours used ({hours_used:.2f})."
                    )
                    continue

                updates.append((new_hours_allotted, hours_used, row["pto_type_id"]))

            if not errors:
                if updates:
                    # Fetch all existing balance records upfront to avoid N+1 queries
                    existing_balances = conn.execute(
                        "SELECT pto_type_id FROM pto_balances WHERE employee_id = ?",
                        (employee_id,),
                    ).fetchall()
                    existing_pto_type_ids = {row["pto_type_id"] for row in existing_balances}

                    for hours_allotted, hours_used, pto_type_id in updates:
                        if pto_type_id in existing_pto_type_ids:
                            conn.execute(
                                """
                                UPDATE pto_balances
                                SET hours_allotted = ?
                                WHERE employee_id = ? AND pto_type_id = ?
                                """,
                                (hours_allotted, employee_id, pto_type_id),
                            )
                        else:
                            conn.execute(
                                """
                                INSERT INTO pto_balances (employee_id, pto_type_id, hours_allotted, hours_used)
                                VALUES (?, ?, ?, ?)
                                """,
                                (employee_id, pto_type_id, hours_allotted, hours_used),
                            )

                    conn.commit()
                    conn.close()
                    flash("PTO balances updated.", "success")
                    return redirect(
                        url_for("employee_detail", employee_id=employee_id, _anchor="balances-edit")
                    )
                else:
                    flash("No PTO balances were changed.", "info")

        if errors:
            flash("Please fix the errors below.", "error")

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

    balance_rows = build_balance_rows(pto_rows, form_data if errors else None)

    # Derive balances for read-only view from balance_rows to avoid duplication
    balances = []
    for row in balance_rows:
        hours_allotted = row["hours_allotted"] if row["hours_allotted"] is not None else 0.0
        hours_used = row["hours_used"]
        balances.append(
            {
                "pto_name": row["display_name"],
                "hours_allotted": hours_allotted,
                "hours_used": hours_used,
                "hours_remaining": hours_allotted - hours_used,
            }
        )

    return render_template(
        "employee_detail.html",
        employee=employee,
        balances=balances,
        pto_entries=pto_entries,
        balance_rows=balance_rows,
        errors=errors,
        is_admin=is_admin,
    )



@app.route("/employees/<int:employee_id>/pto/new", methods=["GET", "POST"])
@login_required
def pto_entry_new(employee_id):
    conn = get_db_connection()

    # Get employee (for page header / validation)
    employee = conn.execute(
        "SELECT id, first_name, last_name FROM employees WHERE id = ?",
        (employee_id,),
    ).fetchone()

    if employee is None:
        conn.close()
        return "Employee not found", 404

    # PTO types for dropdown
    pto_types = conn.execute(
        """
        SELECT id, code, display_name
        FROM pto_types
        WHERE is_active = 1
        ORDER BY display_name
        """
    ).fetchall()

    if request.method == "POST":
        pto_type_id = request.form.get("pto_type_id", "").strip()
        start_date = request.form.get("start_date", "").strip()
        end_date = request.form.get("end_date", "").strip()
        hours_str = request.form.get("hours", "").strip()
        notes = request.form.get("notes", "").strip()

        errors = []

        # Validate pto_type_id exists
        try:
            pto_type_id_int = int(pto_type_id)
        except ValueError:
            pto_type_id_int = None
        if not pto_type_id_int:
            errors.append("Please select a PTO type.")

        if not start_date:
            errors.append("Start date is required.")
        if not end_date:
            errors.append("End date is required.")

        # Validate hours
        try:
            hours = float(hours_str)
            if hours <= 0:
                errors.append("Hours must be greater than 0.")
        except ValueError:
            errors.append("Hours must be a valid number (e.g. 8 or 4.5).")
            hours = None

        # Optional: ensure balance row exists and check remaining hours
        if pto_type_id_int and hours is not None:
            balance = conn.execute(
                """
                SELECT hours_allotted, hours_used
                FROM pto_balances
                WHERE employee_id = ? AND pto_type_id = ?
                """,
                (employee_id, pto_type_id_int),
            ).fetchone()

            if balance is None:
                errors.append("No PTO balance found for this PTO type.")
            else:
                remaining = balance["hours_allotted"] - balance["hours_used"]
                if hours > remaining:
                    errors.append(
                        f"Not enough PTO remaining. Remaining: {remaining:.2f} hours."
                    )

        if errors:
            conn.close()
            return render_template(
                "pto_entry_form.html",
                employee=employee,
                pto_types=pto_types,
                errors=errors,
                form_data={
                    "pto_type_id": pto_type_id,
                    "start_date": start_date,
                    "end_date": end_date,
                    "hours": hours_str,
                    "notes": notes,
                },
            )

        # Insert PTO entry
        conn.execute(
            """
            INSERT INTO pto_entries
                (employee_id, pto_type_id, start_date, end_date, hours, notes, created_by_manager_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (employee_id, pto_type_id_int, start_date, end_date, hours, notes, session.get("user_id")),
        )

        # Update used hours
        conn.execute(
            """
            UPDATE pto_balances
            SET hours_used = hours_used + ?
            WHERE employee_id = ? AND pto_type_id = ?
            """,
            (hours, employee_id, pto_type_id_int),
        )

        conn.commit()
        conn.close()

        return redirect(url_for("employee_detail", employee_id=employee_id))

    # GET request
    conn.close()
    return render_template(
        "pto_entry_form.html",
        employee=employee,
        pto_types=pto_types,
        form_data={}
    )


@app.route("/calendar")
@login_required
def calendar_view():
    # Query params
    selected_employee = request.args.get("employee_id", "all").strip()
    month_str = request.args.get("month", "").strip()  # format YYYY-MM

    # Default to current month if not provided
    if not month_str:
        today = date.today()
        month_str = f"{today.year:04d}-{today.month:02d}"

    # Parse month
    try:
        year = int(month_str.split("-")[0])
        month = int(month_str.split("-")[1])
        _, last_day = cal.monthrange(year, month)
        month_start = date(year, month, 1)
        month_end = date(year, month, last_day)
    except Exception:
        return "Invalid month format. Use YYYY-MM.", 400

    conn = get_db_connection()

    # Employees for dropdown
    employees = conn.execute(
        """
        SELECT id, first_name, last_name
        FROM employees
        WHERE status = 'active'
        ORDER BY last_name, first_name
        """
    ).fetchall()

    # Build query for PTO entries overlapping the month:
    # overlap condition: start_date <= month_end AND end_date >= month_start
    params = [month_end.isoformat(), month_start.isoformat()]
    employee_filter_sql = ""

    if selected_employee != "all":
        try:
            employee_id_int = int(selected_employee)
            employee_filter_sql = "AND e.employee_id = ?"
            params.append(employee_id_int)
        except ValueError:
            conn.close()
            return "Invalid employee_id", 400

    entries = conn.execute(
        f"""
        SELECT
            e.id,
            e.start_date,
            e.end_date,
            e.hours,
            e.notes,
            pt.display_name AS pto_name,
            emp.first_name AS emp_first,
            emp.last_name AS emp_last
        FROM pto_entries e
        JOIN pto_types pt ON pt.id = e.pto_type_id
        JOIN employees emp ON emp.id = e.employee_id
        WHERE
            e.start_date <= ?
            AND e.end_date >= ?
            {employee_filter_sql}
        ORDER BY e.start_date ASC, emp.last_name ASC, emp.first_name ASC
        """,
        tuple(params),
    ).fetchall()

    conn.close()

    return render_template(
        "calendar.html",
        employees=employees,
        entries=entries,
        selected_employee=selected_employee,
        month_str=month_str,
        month_start=month_start.isoformat(),
        month_end=month_end.isoformat(),
    )


@app.route("/admin/balances")
@admin_or_manager_required
def admin_balances_select_employee():
    conn = get_db_connection()
    employees = conn.execute(
        """
        SELECT id, first_name, last_name
        FROM employees
        WHERE status = 'active'
        ORDER BY last_name, first_name
        """
    ).fetchall()
    conn.close()

    return render_template(
        "admin_balances_select_employee.html",
        employees=employees,
    )


def build_balance_rows(pto_rows, form_data=None):
    rows = []
    for row in pto_rows:
        hours_allotted = row["hours_allotted"]
        hours_used = row["hours_used"] if row["hours_used"] is not None else 0.0

        if form_data is not None:
            input_value = form_data.get(str(row["pto_type_id"]), "")
        else:
            input_value = "" if hours_allotted is None else f"{hours_allotted:g}"

        remaining = (
            None
            if hours_allotted is None
            else float(hours_allotted) - float(hours_used)
        )

        rows.append(
            {
                "pto_type_id": row["pto_type_id"],
                "display_name": row["display_name"],
                "hours_allotted": hours_allotted,
                "hours_used": hours_used,
                "remaining": remaining,
                "input_value": input_value,
            }
        )
    return rows


@app.route("/admin/balances/<int:employee_id>", methods=["GET"])
@admin_or_manager_required
def admin_balances_edit(employee_id):
    return redirect(url_for("employee_detail", employee_id=employee_id))


@app.route("/admin/pto-types", methods=["GET"])
@admin_required
def admin_pto_types():
    return render_admin_pto_types()


@app.route("/admin/pto-types/new", methods=["POST"])
@admin_required
def admin_pto_type_new():
    errors = []

    code_raw = request.form.get("code", "")
    display_name = request.form.get("display_name", "").strip()
    default_hours_str = request.form.get("default_hours", "").strip()

    normalized_code = re.sub(r"[^A-Za-z0-9]+", "_", code_raw.strip().upper()).strip("_")

    if not normalized_code:
        errors.append("Code is required and must contain letters or numbers.")
    if not display_name:
        errors.append("Display name is required.")
    
    # Validate default_hours
    if not default_hours_str:
        errors.append("Default hours is required.")
        default_hours = None
    else:
        try:
            default_hours = float(default_hours_str)
            if default_hours < 0:
                errors.append("Default hours must be greater than or equal to 0.")
        except ValueError:
            errors.append("Default hours must be a valid number.")
            default_hours = None

    if not errors:
        conn = get_db_connection()
        try:
            cur = conn.execute(
                """
                INSERT INTO pto_types (code, display_name, is_active, default_hours)
                VALUES (?, ?, 1, ?)
                """,
                (normalized_code, display_name, default_hours),
            )
            pto_type_id = cur.lastrowid

            # Create default balances for active employees so the new PTO type is usable immediately.
            employees = conn.execute(
                "SELECT id FROM employees WHERE status = 'active'"
            ).fetchall()
            balance_rows = [
                (emp["id"], pto_type_id, default_hours, 0.0) for emp in employees
            ]
            if balance_rows:
                conn.executemany(
                    """
                    INSERT OR IGNORE INTO pto_balances (employee_id, pto_type_id, hours_allotted, hours_used)
                    VALUES (?, ?, ?, ?)
                    """,
                    balance_rows,
                )

            conn.commit()
            flash("PTO type added.")
            return redirect(url_for("admin_pto_types"))
        except sqlite3.IntegrityError:
            errors.append("Code must be unique.")
            conn.rollback()
        finally:
            conn.close()

    return render_admin_pto_types(errors)


@app.route("/admin/pto-types/<int:pto_type_id>/edit", methods=["POST"])
@admin_required
def admin_pto_type_edit(pto_type_id):
    display_name = request.form.get("display_name", "").strip()
    default_hours_str = request.form.get("default_hours", "").strip()
    update_all_balances = request.form.get("update_all_balances") == "1"
    errors = []

    if not display_name:
        errors.append("Display name is required.")
    
    # Validate default_hours if provided
    default_hours = None
    if default_hours_str:
        try:
            default_hours = float(default_hours_str)
            if default_hours < 0:
                errors.append("Default hours must be greater than or equal to 0.")
        except ValueError:
            errors.append("Default hours must be a valid number.")

    if not errors:
        conn = get_db_connection()
        cur = conn.execute("SELECT id, default_hours FROM pto_types WHERE id = ?", (pto_type_id,))
        existing = cur.fetchone()
        if existing is None:
            conn.close()
            abort(404)
        
        # Use existing default_hours if not provided in the form
        if default_hours is None:
            default_hours = existing["default_hours"]

        conn.execute(
            """
            UPDATE pto_types
            SET display_name = ?, default_hours = ?
            WHERE id = ?
            """,
            (display_name, default_hours, pto_type_id),
        )

        # Only update all employee balances if explicitly requested
        if update_all_balances:
            conn.execute(
                """
                UPDATE pto_balances
                SET hours_allotted = ?
                WHERE pto_type_id = ?
                """,
                (default_hours, pto_type_id),
            )
            flash("PTO type updated and all employee balances updated.")
        else:
            flash("PTO type updated.")
        
        conn.commit()
        conn.close()
        return redirect(url_for("admin_pto_types"))

    return render_admin_pto_types(errors)


@app.route("/admin/pto-types/<int:pto_type_id>/toggle", methods=["POST"])
@admin_required
def admin_pto_type_toggle(pto_type_id):
    conn = get_db_connection()
    pto_type = conn.execute(
        "SELECT id, is_active FROM pto_types WHERE id = ?",
        (pto_type_id,),
    ).fetchone()

    if pto_type is None:
        conn.close()
        abort(404)

    new_status = 0 if pto_type["is_active"] else 1
    conn.execute(
        "UPDATE pto_types SET is_active = ? WHERE id = ?",
        (new_status, pto_type_id),
    )
    conn.commit()
    conn.close()

    flash("PTO type deactivated." if new_status == 0 else "PTO type reactivated.")
    return redirect(url_for("admin_pto_types"))


@app.route("/admin/pto-types/<int:pto_type_id>/delete", methods=["POST"])
@admin_required
def admin_pto_type_delete(pto_type_id):
    errors = []
    conn = get_db_connection()

    pto_type = conn.execute(
        "SELECT id, display_name FROM pto_types WHERE id = ?",
        (pto_type_id,),
    ).fetchone()
    if pto_type is None:
        conn.close()
        abort(404)

    balances_with_usage = conn.execute(
        """
        SELECT COUNT(*)
        FROM pto_balances
        WHERE pto_type_id = ? AND hours_used > 0
        """,
        (pto_type_id,),
    ).fetchone()[0]
    entries_count = conn.execute(
        "SELECT COUNT(*) FROM pto_entries WHERE pto_type_id = ?",
        (pto_type_id,),
    ).fetchone()[0]

    if balances_with_usage > 0 or entries_count > 0:
        errors.append(
            "Cannot delete PTO type; it is in use. Deactivate instead."
        )
        conn.close()
        return render_admin_pto_types(errors)

    conn.execute("DELETE FROM pto_balances WHERE pto_type_id = ?", (pto_type_id,))
    conn.execute("DELETE FROM pto_types WHERE id = ?", (pto_type_id,))
    conn.commit()
    conn.close()
    flash("PTO type deleted.")

    return redirect(url_for("admin_pto_types"))

def render_admin_pto_types(errors=None):
    conn = get_db_connection()
    ensure_default_pto_types(conn)
    pto_types = conn.execute(
        """
        SELECT id, code, display_name, is_active, default_hours
        FROM pto_types
        ORDER BY is_active DESC, display_name
        """,
    ).fetchall()
    conn.close()

    return render_template(
        "admin_pto_types.html",
        pto_types=pto_types,
        errors=errors or [],
    )

if __name__ == "__main__":
    app.run(debug=True)


