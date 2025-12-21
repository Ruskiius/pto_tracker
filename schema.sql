-- Drop tables if you re-run during dev
DROP TABLE IF EXISTS pto_entries;
DROP TABLE IF EXISTS pto_balances;
DROP TABLE IF EXISTS pto_types;
DROP TABLE IF EXISTS employees;
DROP TABLE IF EXISTS managers;

-- Managers (people who log into the app)
CREATE TABLE managers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    full_name TEXT,
    role TEXT NOT NULL DEFAULT 'manager'  -- 'admin' or 'manager'
);

-- Employees (the 12 employees you're tracking PTO for)
CREATE TABLE employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    employment_type TEXT NOT NULL,  -- 'hourly' or 'salaried'
    phone TEXT,
    email TEXT,
    status TEXT NOT NULL DEFAULT 'active'  -- 'active' or 'inactive'
);



-- PTO balances per employee per PTO type
CREATE TABLE pto_balances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL,
    pto_type_id INTEGER NOT NULL,
    hours_allotted REAL NOT NULL DEFAULT 0,
    hours_used REAL NOT NULL DEFAULT 0,
    FOREIGN KEY (employee_id) REFERENCES employees(id),
    FOREIGN KEY (pto_type_id) REFERENCES pto_types(id),
    UNIQUE (employee_id, pto_type_id)
);

-- Individual PTO entries (what you'll show on the calendar)
CREATE TABLE pto_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL,
    pto_type_id INTEGER NOT NULL,
    start_date TEXT NOT NULL,   -- store as 'YYYY-MM-DD'
    end_date TEXT NOT NULL,
    hours REAL,                 -- optional, for partial days
    notes TEXT,
    created_by_manager_id INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (employee_id) REFERENCES employees(id),
    FOREIGN KEY (pto_type_id) REFERENCES pto_types(id),
    FOREIGN KEY (created_by_manager_id) REFERENCES managers(id)

);

-- PTO types (Personal, Sick, Vacation)
CREATE TABLE pto_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,         -- e.g. 'PERSONAL'
    display_name TEXT NOT NULL,        -- e.g. 'Personal Time'
    is_active INTEGER NOT NULL DEFAULT 1
);

