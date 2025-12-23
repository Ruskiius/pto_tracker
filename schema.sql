PRAGMA foreign_keys = ON;

-- Drop tables if you re-run during dev (reverse dependency order)
DROP TABLE IF EXISTS pto_entries;
DROP TABLE IF EXISTS pto_balances;
DROP TABLE IF EXISTS employees;
DROP TABLE IF EXISTS pto_types;
DROP TABLE IF EXISTS managers;

-- Managers (people who log into the app)
CREATE TABLE managers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    full_name TEXT,
    role TEXT NOT NULL DEFAULT 'manager'
);

-- Employees
CREATE TABLE employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    employment_type TEXT NOT NULL CHECK (employment_type IN ('hourly', 'salaried')),
    phone TEXT,
    email TEXT,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive'))
);

-- PTO types (Personal, Sick, Vacation, etc.)
CREATE TABLE pto_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    default_hours REAL NOT NULL DEFAULT 40
);

-- PTO balances per employee per PTO type
CREATE TABLE pto_balances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL,
    pto_type_id INTEGER NOT NULL,
    hours_allotted REAL NOT NULL DEFAULT 0,
    hours_used REAL NOT NULL DEFAULT 0,
    UNIQUE (employee_id, pto_type_id),
    FOREIGN KEY (employee_id) REFERENCES employees(id),
    FOREIGN KEY (pto_type_id) REFERENCES pto_types(id)
);

-- PTO entries (calendar items)
CREATE TABLE pto_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL,
    pto_type_id INTEGER NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    hours REAL,
    notes TEXT,
    created_by_manager_id INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (employee_id) REFERENCES employees(id),
    FOREIGN KEY (pto_type_id) REFERENCES pto_types(id),
    FOREIGN KEY (created_by_manager_id) REFERENCES managers(id)
);
