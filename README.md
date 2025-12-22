# PTO Tracker

This repository contains a small Flask application for tracking employee PTO balances. Use the helper scripts below to recreate the SQLite database during development and to log in with the default admin account.

## Resetting the database
1. From the repository root, run the initialization script:
   ```bash
   python init_db.py
   ```
   This recreates `pto_tracker.db` from `schema.sql` and seeds PTO types along with the default admin user.

2. Restart the Flask app after reinitializing the database. If you are running it locally, you can start it with:
   ```bash
   python app.py
   ```

3. Sign in with the seeded admin credentials:
   - **Username:** `admin`
   - **Password:** `password`

> Tip: You can change the admin password in `init_db.py` before seeding or update it directly in the database after initialization for better security.
