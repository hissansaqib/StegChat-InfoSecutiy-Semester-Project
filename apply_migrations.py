"""
apply_migrations.py
Applies any missing column additions to stegchat.db so it matches the current SQLAlchemy models.
Safe to re-run: each ALTER TABLE is guarded by checking existing columns first.
"""
import sqlite3
import sys

DB_PATH = "stegchat.db"

def get_columns(conn, table):
    cur = conn.execute(f"PRAGMA table_info({table})")
    return {row[1] for row in cur.fetchall()}

def add_col_if_missing(conn, table, col_name, col_def):
    cols = get_columns(conn, table)
    if col_name not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_def}")
        print(f"  + Added {table}.{col_name}")
    else:
        print(f"  = {table}.{col_name} already exists")

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")

    print("[messages] Checking columns...")
    add_col_if_missing(conn, "messages", "mode", "VARCHAR NOT NULL DEFAULT 'normal'")
    add_col_if_missing(conn, "messages", "attachment_id", "VARCHAR REFERENCES attachments(id)")

    print("[experiment_runs] Checking columns...")
    add_col_if_missing(conn, "experiment_runs", "owner_id", "VARCHAR")
    add_col_if_missing(conn, "experiment_runs", "suite_id", "VARCHAR")
    add_col_if_missing(conn, "experiment_runs", "seed", "VARCHAR")
    add_col_if_missing(conn, "experiment_runs", "config", "JSON")
    add_col_if_missing(conn, "experiment_runs", "capacity_bytes", "INTEGER")
    add_col_if_missing(conn, "experiment_runs", "size_overhead", "INTEGER")
    add_col_if_missing(conn, "experiment_runs", "recovered", "BOOLEAN DEFAULT 0")
    add_col_if_missing(conn, "experiment_runs", "measurements", "JSON")
    add_col_if_missing(conn, "experiment_runs", "hashes", "JSON")
    add_col_if_missing(conn, "experiment_runs", "module_version", "VARCHAR")
    add_col_if_missing(conn, "experiment_runs", "error_code", "VARCHAR")

    conn.commit()
    conn.close()
    print("\nMigration complete.")

if __name__ == "__main__":
    main()

