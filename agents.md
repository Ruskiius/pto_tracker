# AGENTS.md – Project Context for AI Contributors

## Project Overview
This is a Flask-based internal PTO (Paid Time Off) tracking application.

- Stack: Flask, SQLite, Werkzeug, server-rendered HTML (Jinja)
- Audience: Managers only (no employee self-service yet)
- Scale: ~12 employees
- Philosophy: Simple, explicit, boring > clever

This project is intentionally NOT a microservice, SPA, or React app.

---

## Core Concepts (DO NOT VIOLATE)

- Authentication is session-based (Flask sessions)
- Roles:
  - admin
  - manager
- Admins have elevated privileges
- Managers can view/add PTO but not modify system configuration
- SQLite is the source of truth
- Soft deletes are preferred over hard deletes where history matters

---

## Current Features (Implemented)

- Manager login (username/password, hashed)
- Employee CRUD (create + view)
- PTO balances per employee per PTO type
- PTO entries with automatic balance updates
- Calendar view with filters
- Admin-only PTO type management:
  - Edit name
  - Deactivate (soft delete)
  - Delete (hard delete when safe)

---

## PTO Types Rules

- PTO types are stored in `pto_types`
- PTO types may be:
  - Active
  - Deactivated (hidden, but historical data preserved)
- Deleting a PTO type is only allowed if:
  - No PTO entries reference it
- Deactivation is preferred over deletion

---

## Definition of Done (IMPORTANT)

A feature is considered DONE only if:

- Role checks are enforced server-side
- Database integrity is preserved
- UI reflects permissions correctly
- No silent data corruption
- No breaking existing functionality
- Code follows existing style patterns
- No unnecessary abstractions

---

## What NOT to Do

- Do NOT introduce React, Vue, or SPA patterns
- Do NOT convert auth to JWT
- Do NOT auto-migrate schemas without explicit approval
- Do NOT remove soft-delete behavior without discussion
- Do NOT “simplify” by deleting history

---

## AI Instructions

If you are an AI agent:

- Read this file before making changes
- Prefer small, incremental changes
- Ask for clarification if unsure
- Preserve existing behavior unless explicitly instructed otherwise
