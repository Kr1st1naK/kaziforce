"""Shared fixtures. The PostgreSQL ones are skipped unless DATABASE_URL is set (CI has no database)."""

import os
import uuid

import numpy as np
import pytest
from dotenv import load_dotenv

load_dotenv()

# Tests build their own keys. Setting this before anything imports the app keeps a machine
# with no .env (CI) from being treated as production and refusing to start without keys.
os.environ.setdefault("KAZIFORCE_ENV", "test")

DATABASE_URL = os.getenv("DATABASE_URL")
requires_db = pytest.mark.skipif(not DATABASE_URL, reason="DATABASE_URL not set (no database)")


@pytest.fixture(scope="module")
def pg_connect():
    """A connect() for a throwaway, migrated schema; dropped afterwards, so existing tables are untouched."""
    import psycopg2

    from kaziforce_api.data.migrate import migration_files

    name = f"kaziforce_test_{uuid.uuid4().hex[:8]}"
    admin = psycopg2.connect(DATABASE_URL)
    admin.autocommit = True
    with admin.cursor() as cur:
        cur.execute(f"CREATE SCHEMA {name}")

    def connect():
        return psycopg2.connect(DATABASE_URL, options=f"-c search_path={name}")

    conn = connect()
    with conn, conn.cursor() as cur:
        for path in migration_files():
            cur.execute(path.read_text())
    conn.close()
    try:
        yield connect
    finally:
        with admin.cursor() as cur:
            cur.execute(f"DROP SCHEMA {name} CASCADE")
        admin.close()


@pytest.fixture(scope="module")
def crypto():
    """Fresh random keys, so no test depends on, or leaks, a real one."""
    from kaziforce_api.crypto import FieldCipher, FieldCrypto, generate_key
    import base64

    key = base64.urlsafe_b64decode(generate_key())
    return FieldCrypto(FieldCipher({"v1": key}), base64.urlsafe_b64decode(generate_key()))


@pytest.fixture(scope="module")
def stub_encoder():
    """A deterministic stand-in for the sentence-transformer: letter counts, so no model is downloaded."""
    def encode(texts):
        return np.array([[t.lower().count(c) for c in "abcdefghijklmnopqrstuvwxyz"] for t in texts],
                        dtype=float) + 1e-3

    return encode
