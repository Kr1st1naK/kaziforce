"""
Loads the frozen dataset into PostgreSQL (DATABASE_URL in .env) through the
migrated schema: skills, the development-split worker profiles and all 280 job
postings. Idempotent; re-running gives the same rows.

Apply the migrations first:
    python -m kaziforce_api.data.migrate
    python scripts/seed_database.py

--reset empties every table first, so profiles and postings stored through the
API (a demo, or an end-to-end run) are cleared and the database is left holding
exactly the frozen dataset again.

Only development-split workers are loaded during Sprint II, matching the rule
that no validation or test profile is used before the final evaluation.
"""

from __future__ import annotations

import argparse

from kaziforce_api.data.data_loader import DataLoader
from kaziforce_api.data.db import get_connection
from kaziforce_api.data.migrate import applied_versions, migration_files
from kaziforce_api.data.seed import reset, seed, skill_rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--split", default="development", choices=["development"])
    parser.add_argument("--reset", action="store_true",
                        help="delete everything first, including profiles and postings stored through the API")
    args = parser.parse_args()

    conn = get_connection()
    try:
        pending = [p.stem for p in migration_files() if p.stem not in applied_versions(conn)]
        if pending:
            raise SystemExit(f"pending migrations {pending}: run python -m kaziforce_api.data.migrate first")
        if args.reset:
            deleted = reset(conn)
            print("Deleted: " + ", ".join(f"{table} {n}" for table, n in deleted.items() if n))
        loader = DataLoader()
        workers, jobs = loader.workers(args.split), loader.jobs()
        counts = seed(conn, workers, jobs, skill_rows(workers, jobs))
    finally:
        conn.close()
    print("Seeded: " + ", ".join(f"{table} {n}" for table, n in counts.items()))


if __name__ == "__main__":
    main()
