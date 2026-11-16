"""
Database connection helper.

Reads DATABASE_URL from .env (works for both Supabase and local PostgreSQL —
see .env.example and README.md "Database Setup").

Two timeouts are set here, because an unreachable or wedged database should
surface as an error the API can report rather than a request that never returns
(IR-06):

- **connect_timeout** bounds how long opening a connection may take. Without it,
  an unreachable host can block until the operating system gives up, which on
  some networks is minutes.
- **statement_timeout** bounds how long one query may run. PostgreSQL enforces
  it server-side and cancels the query, so it holds even if the client is stuck
  waiting on the socket.

Both are deliberately generous. They exist to turn a hang into an error, not to
police normal queries: every application query is a single-row lookup or a small
insert, and the slowest measured one is well under 50 ms. Batch work (migrations
and seeding, which insert thousands of rows in one statement) passes
`statement_timeout_ms=None` to opt out.
"""

import os

import psycopg2
from dotenv import load_dotenv

load_dotenv()

CONNECT_TIMEOUT_S = 5
STATEMENT_TIMEOUT_MS = 5_000


def get_connection(statement_timeout_ms: int | None = STATEMENT_TIMEOUT_MS):
    """A connection with IR-06's timeouts applied. `statement_timeout_ms=None` opts out."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL not set. Copy .env.example to .env and fill it in.")
    options = f"-c statement_timeout={statement_timeout_ms}" if statement_timeout_ms is not None else None
    return psycopg2.connect(database_url, connect_timeout=CONNECT_TIMEOUT_S, options=options)


if __name__ == "__main__":
    # Quick manual test: python -m kaziforce_api.data.db
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT version();")
        print(cur.fetchone())
    conn.close()
