# PTO Tracker – AI Agent Reference

This project is a Flask + SQLite PTO tracking app for a small company (≈12 employees).
It is an internal, manager-facing tool (employees do not log in).

## Tech Stack
- Python
- Flask (server-rendered HTML)
- SQLite
- Werkzeug (auth + password hashing)
- No frontend framework (no React)

## Auth & Roles
- Users are "managers"
- Roles:
  - admin
  - manager
- Only admins can:
  - manage PTO types
  - edit PTO balances
  - manage other managers (future)

Role is stored in session as `session["role"]`.

## Core Features Already Implemented
- Manager login (username/password)
- Employee CRUD (soft delete via `status`)
- PTO balances per employee per PTO type
- PTO entry creation (updates balances)
- Calendar view (month + employee filter)
- Admin-only PTO type management:
  - Edit PTO type name
  - Deactivate PTO types (soft delete)
  - Delete PTO types (only if no dependencies)

## PTO Type Rules
- PTO types must NOT be hard-deleted if:
  - PTO entries exist
  - PTO balances exist
- Prefer soft delete (`is_active = 0`)
- Editing name must not break historical entries

## Development Rules
- Do NOT rewrite existing working routes
- Do NOT remove role checks
- Prefer small, incremental changes
- Avoid unnecessary abstractions
- Keep logic in Flask routes, not client-side JS

## Definition of Done (for any feature)
- Role restrictions enforced
- DB integrity preserved
- No existing features broken
- UI accessible from dashboard
- Works with SQLite locally
