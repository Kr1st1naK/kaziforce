"""
Apply versioned SQL migrations to the database in DATABASE_URL.

Migrations are the numbered files in ./migrations (0001_*.sql, 0002_*.sql, ...).
Each pending file runs in its own transaction and is recorded in
schema_migrations, so re-running is a no-op and a fresh database can be
rebuilt from scratch by running this once.

Usage: python -m kaziforce_api.data.migrate [--status]
"""

from __future__ import annotations

import argparse
from pathlib import Path

from kaziforce_api.data.db import get_connection

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


def migration_files() -> list[Path]:
    return sorted(MIGRATIONS_DIR.glob("[0-9][0-9][0-9][0-9]_*.sql"))


def applied_versions(conn) -> set[str]:
    with conn.cursor() as cur:
        cur.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            " version VARCHAR(255) PRIMARY KEY,"
            " applied_at TIMESTAMPTZ NOT NULL DEFAULT now())"
        )
        cur.execute("SELECT version FROM schema_migrations")
        versions = {row[0] for row in cur.fetchall()}
    conn.commit()
    return versions


def migrate() -> list[str]:
    """Apply all pending migrations; return the versions applied."""
    conn = get_connection()
    try:
        done = applied_versions(conn)
        applied = []
        for path in migration_files():
            if path.stem in done:
                continue
            with conn, conn.cursor() as cur:  # one transaction per migration
                cur.execute(path.read_text())
                cur.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (path.stem,))
            applied.append(path.stem)
        return applied
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Apply pending SQL migrations.")
    parser.add_argument("--status", action="store_true", help="list migrations without applying")
    args = parser.parse_args()
    if args.status:
        conn = get_connection()
        done = applied_versions(conn)
        conn.close()
        for path in migration_files():
            print(f"[{'x' if path.stem in done else ' '}] {path.stem}")
    else:
        applied = migrate()
        print("Applied: " + ", ".join(applied) if applied else "Database is up to date.")
