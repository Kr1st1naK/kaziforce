"""
The encrypted-phone migration, rehearsed on accounts created the old way.

A throwaway schema is built up to migration 0003 (plaintext phone), given accounts with real PIN
hashes, then taken through 0004, the backfill and 0005. Sign-in must work at the end, no plaintext
may remain, and the way back must restore it.
"""

import uuid

import psycopg2
import pytest

from kaziforce_api.auth import AuthError, hash_pin
from kaziforce_api.data import backfill_contact
from kaziforce_api.data.accounts import AccountStore
from kaziforce_api.data.migrate import migration_files
from tests.conftest import DATABASE_URL, requires_db

pytestmark = [pytest.mark.db, requires_db]

PIN = "4821"
OLD_ACCOUNTS = [("254700100001", "worker"), ("254700100002", "client"), ("254700100003", "worker")]


def run(connect, *stems_or_sql: str):
    conn = connect()
    with conn, conn.cursor() as cur:
        for item in stems_or_sql:
            path = next((p for p in migration_files() if p.stem == item), None)
            cur.execute(path.read_text() if path else item)
    conn.close()


def columns(connect) -> set[str]:
    conn = connect()
    with conn.cursor() as cur:
        cur.execute("SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema = current_schema() AND table_name = 'account'")
        found = {r[0] for r in cur.fetchall()}
    conn.close()
    return found


@pytest.fixture
def legacy(crypto):
    """A schema at migration 0003 with three plaintext accounts, as the real database was."""
    name = f"kaziforce_mig_{uuid.uuid4().hex[:8]}"
    admin = psycopg2.connect(DATABASE_URL)
    admin.autocommit = True
    with admin.cursor() as cur:
        cur.execute(f"CREATE SCHEMA {name}")

    def connect():
        return psycopg2.connect(DATABASE_URL, options=f"-c search_path={name}")

    run(connect, "0001_initial_schema", "0002_application_store", "0003_accounts",
        "CREATE TABLE schema_migrations (version VARCHAR(255) PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())")
    conn = connect()
    with conn, conn.cursor() as cur:
        for phone, role in OLD_ACCOUNTS:
            pin_hash, salt, iterations = hash_pin(PIN)
            cur.execute("INSERT INTO account (phone, role, pin_hash, pin_salt, pin_iterations) VALUES (%s,%s,%s,%s,%s)",
                        (phone, role, pin_hash, salt, iterations))
    conn.close()
    try:
        yield connect
    finally:
        with admin.cursor() as cur:
            cur.execute(f"DROP SCHEMA {name} CASCADE")
        admin.close()


def test_the_whole_path_leaves_working_sign_in_and_no_plaintext(legacy, crypto):
    run(legacy, "0004_encrypted_contact")
    store = AccountStore(legacy, crypto)

    # Between 0004 and the backfill, an old account has no hash and cannot sign in.
    with pytest.raises(AuthError):
        store.authenticate(OLD_ACCOUNTS[0][0], PIN)

    # 0005 refuses while accounts are unfilled, and changes nothing when it does.
    with pytest.raises(psycopg2.errors.RaiseException, match="backfill_contact"):
        run(legacy, "0005_drop_plaintext_phone")
    assert "phone" in columns(legacy)

    conn = legacy()
    assert backfill_contact.backfill(conn, crypto) == len(OLD_ACCOUNTS)
    assert backfill_contact.verify(conn, crypto) == (len(OLD_ACCOUNTS), 0)
    conn.close()
    run(legacy, "0005_drop_plaintext_phone")

    assert "phone" not in columns(legacy)
    for phone, role in OLD_ACCOUNTS:
        assert store.authenticate(phone, PIN).role == role  # the PIN hash was never touched
    with pytest.raises(AuthError):
        store.authenticate(OLD_ACCOUNTS[0][0], "0000")


def test_after_the_migration_no_plaintext_phone_is_in_any_column(legacy, crypto):
    run(legacy, "0004_encrypted_contact")
    conn = legacy()
    backfill_contact.backfill(conn, crypto)
    conn.close()
    run(legacy, "0005_drop_plaintext_phone")

    conn = legacy()
    with conn.cursor() as cur:
        cur.execute("SELECT row_to_json(a)::text FROM account a")
        dump = " ".join(r[0] for r in cur.fetchall())
    conn.close()
    for phone, _ in OLD_ACCOUNTS:
        assert phone not in dump and phone[3:] not in dump


def test_the_backfill_is_safe_to_run_twice(legacy, crypto):
    run(legacy, "0004_encrypted_contact")
    conn = legacy()
    assert backfill_contact.backfill(conn, crypto) == len(OLD_ACCOUNTS)
    assert backfill_contact.backfill(conn, crypto) == 0
    assert backfill_contact.verify(conn, crypto) == (len(OLD_ACCOUNTS), 0)
    conn.close()


def test_verification_catches_an_account_that_does_not_decrypt(legacy, crypto):
    run(legacy, "0004_encrypted_contact")
    conn = legacy()
    backfill_contact.backfill(conn, crypto)
    with conn, conn.cursor() as cur:
        cur.execute("UPDATE account SET phone_enc = 'v1:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA' "
                    "WHERE phone = %s", (OLD_ACCOUNTS[0][0],))
    assert backfill_contact.verify(conn, crypto) == (len(OLD_ACCOUNTS), 1)
    conn.close()


def test_verification_fails_under_the_wrong_key(legacy, crypto):
    from kaziforce_api.crypto import FieldCipher, FieldCrypto, generate_key
    import base64

    run(legacy, "0004_encrypted_contact")
    conn = legacy()
    backfill_contact.backfill(conn, crypto)
    other = FieldCrypto(FieldCipher({"v1": base64.urlsafe_b64decode(generate_key())}), crypto.phone_hmac_key)
    assert backfill_contact.verify(conn, other) == (len(OLD_ACCOUNTS), len(OLD_ACCOUNTS))
    conn.close()


def test_the_way_back_restores_the_plaintext_column(legacy, crypto):
    run(legacy, "0004_encrypted_contact")
    conn = legacy()
    backfill_contact.backfill(conn, crypto)
    conn.close()
    run(legacy, "0005_drop_plaintext_phone", "INSERT INTO schema_migrations VALUES ('0005_drop_plaintext_phone')")
    # An account made after the migration has never had a plaintext phone.
    created = AccountStore(legacy, crypto).create("254700100099", PIN, "worker")
    assert created.phone == "254700100099"

    conn = legacy()
    assert backfill_contact.restore_plaintext(conn, crypto) == len(OLD_ACCOUNTS) + 1
    with conn.cursor() as cur:
        cur.execute("SELECT phone FROM account ORDER BY phone")
        restored = [r[0] for r in cur.fetchall()]
        cur.execute("SELECT count(*) FROM schema_migrations WHERE version = '0005_drop_plaintext_phone'")
        assert cur.fetchone()[0] == 0  # migrating again will re-apply the guard
    conn.close()
    assert restored == sorted([p for p, _ in OLD_ACCOUNTS] + ["254700100099"])


def test_a_fresh_database_runs_every_migration_straight_through(pg_connect):
    conn = pg_connect()
    with conn.cursor() as cur:
        cur.execute("SELECT column_name, is_nullable FROM information_schema.columns "
                    "WHERE table_schema = current_schema() AND table_name = 'account'")
        found = dict(cur.fetchall())
    conn.close()
    assert "phone" not in found
    assert found["phone_hash"] == "NO" and found["phone_enc"] == "NO"
    assert {"first_name_enc", "last_name_enc", "contact_consent"} <= set(found)
