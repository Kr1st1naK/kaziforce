"""
AccountStore: accounts, sessions, and the ownership links to profiles and postings.

Every method takes or returns plain values; the PIN never leaves auth.py and
the raw session token is returned once, at creation, and never stored.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import datetime, timezone

from kaziforce_api.auth import (
    Account,
    AuthError,
    hash_pin,
    hash_token,
    lockout_until,
    new_session_token,
    pin_matches,
)


def _is_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
    except (ValueError, AttributeError, TypeError):
        return False
    return True


class AccountStore:
    def __init__(self, connect: Callable | None = None):
        if connect is None:
            from kaziforce_api.data.db import get_connection as connect
        self._connect = connect

    # Accounts

    def create(self, phone: str, pin: str, role: str) -> Account:
        """Create an account. Raises AuthError if the phone number is already registered."""
        pin_hash, salt, iterations = hash_pin(pin)
        conn = self._connect()
        try:
            with conn, conn.cursor() as cur:
                cur.execute("SELECT 1 FROM account WHERE phone = %s", (phone,))
                if cur.fetchone():
                    raise AuthError("That phone number already has an account.", "already_exists", "phone")
                cur.execute(
                    "INSERT INTO account (phone, role, pin_hash, pin_salt, pin_iterations) "
                    "VALUES (%s, %s, %s, %s, %s) RETURNING account_id::text",
                    (phone, role, pin_hash, salt, iterations),
                )
                return Account(cur.fetchone()[0], phone, role)
        finally:
            conn.close()

    def authenticate(self, phone: str, pin: str) -> Account:
        """Verify a PIN. Raises AuthError on a wrong PIN, an unknown number, or a locked account.

        The attempt counter is committed before the error is raised: raising inside the
        transaction would roll the counter back and the lockout would never take effect.
        """
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT account_id::text, role, pin_hash, pin_salt, pin_iterations, failed_attempts, locked_until "
                    "FROM account WHERE phone = %s FOR UPDATE",
                    (phone,),
                )
                row = cur.fetchone()
                if row is None:
                    conn.rollback()
                    # Same message as a wrong PIN, so the response does not reveal which numbers exist.
                    raise AuthError("That phone number or PIN is not right.")
                account_id, role, pin_hash, salt, iterations, failed, locked_until = row
                if locked_until and locked_until > datetime.now(timezone.utc):
                    conn.rollback()
                    raise AuthError("Too many tries. Wait a few minutes and try again.", "locked")
                if not pin_matches(pin, pin_hash, salt, iterations):
                    failed += 1
                    cur.execute("UPDATE account SET failed_attempts = %s, locked_until = %s WHERE account_id = %s",
                                (failed, lockout_until(failed), account_id))
                    conn.commit()
                    raise AuthError("That phone number or PIN is not right.")
                cur.execute("UPDATE account SET failed_attempts = 0, locked_until = NULL WHERE account_id = %s",
                            (account_id,))
                conn.commit()
                return Account(account_id, phone, role)
        finally:
            conn.close()

    # Sessions

    def start_session(self, account_id: str) -> str:
        """Create a session and return the token for the cookie. Only its hash is stored."""
        token, token_hash, expires_at = new_session_token()
        conn = self._connect()
        try:
            with conn, conn.cursor() as cur:
                cur.execute("INSERT INTO session (token_hash, fk_account_id, expires_at) VALUES (%s, %s, %s)",
                            (token_hash, account_id, expires_at))
        finally:
            conn.close()
        return token

    def session_account(self, token: str | None) -> Account | None:
        """The account behind a cookie value, or None if it is missing, unknown or expired."""
        if not token:
            return None
        conn = self._connect()
        try:
            with conn, conn.cursor() as cur:
                cur.execute(
                    "SELECT a.account_id::text, a.phone, a.role FROM session s "
                    "JOIN account a ON a.account_id = s.fk_account_id "
                    "WHERE s.token_hash = %s AND s.expires_at > now()",
                    (hash_token(token),),
                )
                row = cur.fetchone()
                return Account(*row) if row else None
        finally:
            conn.close()

    def end_session(self, token: str | None) -> None:
        if not token:
            return
        conn = self._connect()
        try:
            with conn, conn.cursor() as cur:
                cur.execute("DELETE FROM session WHERE token_hash = %s", (hash_token(token),))
        finally:
            conn.close()

    # Ownership

    def worker_profile_id(self, account_id: str) -> str | None:
        """The profile this worker account owns, if it has created one."""
        conn = self._connect()
        try:
            with conn, conn.cursor() as cur:
                cur.execute("SELECT worker_id::text FROM worker_profile WHERE fk_account_id = %s", (account_id,))
                row = cur.fetchone()
                return row[0] if row else None
        finally:
            conn.close()

    def claim_worker_profile(self, account_id: str, worker_id: str) -> None:
        conn = self._connect()
        try:
            with conn, conn.cursor() as cur:
                cur.execute("UPDATE worker_profile SET fk_account_id = %s WHERE worker_id = %s",
                            (account_id, worker_id))
        finally:
            conn.close()

    def claim_job_posting(self, account_id: str, posting_id: str) -> None:
        conn = self._connect()
        try:
            with conn, conn.cursor() as cur:
                cur.execute("UPDATE job_posting SET fk_account_id = %s WHERE posting_id = %s",
                            (account_id, posting_id))
        finally:
            conn.close()

    def posting_ids(self, account_id: str) -> list[str]:
        """This client's postings, newest first."""
        conn = self._connect()
        try:
            with conn, conn.cursor() as cur:
                cur.execute("SELECT posting_id::text FROM job_posting WHERE fk_account_id = %s "
                            "ORDER BY created_at DESC, posting_id", (account_id,))
                return [r[0] for r in cur.fetchall()]
        finally:
            conn.close()

    def owns_posting(self, account_id: str, posting_id: str) -> bool:
        if not _is_uuid(posting_id):
            return False
        conn = self._connect()
        try:
            with conn, conn.cursor() as cur:
                cur.execute("SELECT 1 FROM job_posting WHERE posting_id = %s AND fk_account_id = %s",
                            (posting_id, account_id))
                return cur.fetchone() is not None
        finally:
            conn.close()
