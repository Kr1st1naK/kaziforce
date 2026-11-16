"""
Encrypt the phone numbers already in the account table, and check that it worked.

Run after migration 0004 and before 0005 (see docs/privacy-and-keys.md):

    python -m kaziforce_api.data.backfill_contact                      encrypt, then verify
    python -m kaziforce_api.data.backfill_contact --verify-only        verify only
    python -m kaziforce_api.data.backfill_contact --restore-plaintext  the way back

Verifying means decrypting every phone_enc, comparing it with the plaintext still in the table,
and recomputing phone_hash. It exits non-zero on the first account that does not match, and
nothing here drops anything: 0005 does that, and it refuses to run until this has filled every
row. The keys are read from the environment, so the backfill must use the keys the API will use.

This prints counts only. It never prints a phone number, a hash or a key.
"""

from __future__ import annotations

import argparse
import sys

from kaziforce_api.crypto import CryptoError, FieldCrypto, load_from_env
from kaziforce_api.data.db import get_connection

DROPPED = "0005_drop_plaintext_phone"


def backfill(conn, crypto: FieldCrypto) -> int:
    """Encrypt every account that still has only a plaintext phone. Returns how many."""
    with conn, conn.cursor() as cur:
        cur.execute("SELECT account_id, phone FROM account WHERE phone IS NOT NULL AND "
                    "(phone_hash IS NULL OR phone_enc IS NULL) FOR UPDATE")
        rows = cur.fetchall()
        for account_id, phone in rows:
            cur.execute("UPDATE account SET phone_hash = %s, phone_enc = %s WHERE account_id = %s",
                        (crypto.phone_hash(phone), crypto.encrypt_phone(phone), account_id))
    return len(rows)


def verify(conn, crypto: FieldCrypto) -> tuple[int, int]:
    """(accounts checked, accounts that do not match). Every account must have an encrypted phone."""
    bad = 0
    with conn.cursor() as cur:
        cur.execute("SELECT phone, phone_hash, phone_enc FROM account")
        rows = cur.fetchall()
    conn.rollback()
    for phone, phone_hash, phone_enc in rows:
        try:
            decrypted = crypto.decrypt_phone(phone_enc) if phone_enc else None
        except CryptoError:
            decrypted = None
        ok = (decrypted is not None and phone_hash == crypto.phone_hash(decrypted)
              and (phone is None or phone == decrypted))
        bad += 0 if ok else 1
    return len(rows), bad


def restore_plaintext(conn, crypto: FieldCrypto) -> int:
    """Put the plaintext phone column back, filled from phone_enc, so the previous code can run.

    Also lets the NOT NULL on the new columns go (the previous code does not write them) and
    forgets that 0005 ran, so migrating again re-applies its guard. Returns accounts restored.
    """
    with conn, conn.cursor() as cur:
        cur.execute("ALTER TABLE account ADD COLUMN IF NOT EXISTS phone VARCHAR(20)")
        cur.execute("ALTER TABLE account ALTER COLUMN phone_hash DROP NOT NULL, ALTER COLUMN phone_enc DROP NOT NULL")
        cur.execute("SELECT account_id, phone_enc FROM account WHERE phone IS NULL")
        rows = cur.fetchall()
        for account_id, phone_enc in rows:
            cur.execute("UPDATE account SET phone = %s WHERE account_id = %s",
                        (crypto.decrypt_phone(phone_enc), account_id))
        cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS account_phone_key ON account (phone)")
        cur.execute("ALTER TABLE account ALTER COLUMN phone SET NOT NULL")
        cur.execute("DELETE FROM schema_migrations WHERE version = %s", (DROPPED,))
    return len(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Encrypt existing phone numbers and verify them.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--verify-only", action="store_true", help="check without changing anything")
    mode.add_argument("--restore-plaintext", action="store_true", help="re-create the plaintext phone column (rollback)")
    args = parser.parse_args(argv)

    crypto = load_from_env()
    conn = get_connection(statement_timeout_ms=None)
    try:
        if args.restore_plaintext:
            print(f"restored the plaintext phone for {restore_plaintext(conn, crypto)} accounts")
            return 0
        if not args.verify_only:
            print(f"encrypted {backfill(conn, crypto)} accounts")
        checked, bad = verify(conn, crypto)
        print(f"verified {checked - bad} of {checked} accounts")
        if bad:
            print("NOT SAFE TO CONTINUE: some accounts did not decrypt or did not match. Do not run migration 0005.")
            return 1
        print("Now run: python -m kaziforce_api.data.migrate")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
