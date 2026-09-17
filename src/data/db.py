"""
Database connection helper.

Reads DATABASE_URL from .env (works for both Supabase and local PostgreSQL —
see .env.example and README.md "Database Setup").
"""

import os

import psycopg2
from dotenv import load_dotenv

load_dotenv()


def get_connection():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL not set. Copy .env.example to .env and fill it in.")
    return psycopg2.connect(database_url)


if __name__ == "__main__":
    # Quick manual test: python -m src.data.db
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT version();")
        print(cur.fetchone())
    conn.close()
