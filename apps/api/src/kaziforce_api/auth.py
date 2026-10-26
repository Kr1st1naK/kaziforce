"""
Accounts, PINs and sessions.

A phone number and a 4-digit PIN identify an account, which carries a role:
`worker` or `client`. The PIN is stored only as a PBKDF2-HMAC-SHA256 hash with
a per-account salt; the session cookie value is stored only as a SHA-256 hash.
Neither the PIN nor the raw token is ever stored, logged or returned.

**This is a proof of concept, not a security control.** A 4-digit PIN has
10,000 combinations, so anyone holding a copy of the database can recover PINs
by brute force whatever hashing is used. Online guessing is slowed by locking
an account after MAX_FAILED_ATTEMPTS. See docs/limitations.md §7.
"""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

ROLES = ("worker", "client")
PIN_LENGTH = 4
PIN_ITERATIONS = 600_000  # OWASP's 2023 floor for PBKDF2-HMAC-SHA256
SALT_BYTES = 16
TOKEN_BYTES = 32
SESSION_LIFETIME = timedelta(days=7)
MAX_FAILED_ATTEMPTS = 5
LOCKOUT = timedelta(minutes=15)

COUNTRY_CODE = "254"
_PIN_RE = re.compile(rf"^\d{{{PIN_LENGTH}}}$")
_DIGITS_RE = re.compile(r"\D")


class AuthError(ValueError):
    """A sign-in or account problem that is safe to report to the client."""

    def __init__(self, message: str, code: str = "invalid_credentials", field: str | None = None):
        super().__init__(message)
        self.code = code
        self.field = field


@dataclass(frozen=True)
class Account:
    account_id: str
    phone: str
    role: str


def normalise_phone(value: str) -> str:
    """Kenyan mobile number to E.164 digits without '+': 0712 345 678 -> 254712345678.

    Accepts the local form, the national form, and the international form with or without '+'.
    """
    digits = _DIGITS_RE.sub("", value or "")
    if digits.startswith("0"):
        digits = COUNTRY_CODE + digits[1:]
    elif not digits.startswith(COUNTRY_CODE):
        digits = COUNTRY_CODE + digits
    if len(digits) != 12:
        raise AuthError("Enter a phone number like 712 345 678.", "invalid_request", "phone")
    return digits


def local_phone(phone: str) -> str:
    """The part a person types, for display: 254712345678 -> 712345678."""
    return phone[len(COUNTRY_CODE):] if phone.startswith(COUNTRY_CODE) else phone


def check_role(value: str) -> str:
    if value not in ROLES:
        raise AuthError(f"Role must be one of {', '.join(ROLES)}.", "invalid_request", "role")
    return value


def check_pin(value: str) -> str:
    """The PIN itself, validated. Never log the return value."""
    if not isinstance(value, str) or not _PIN_RE.match(value):
        raise AuthError(f"Your PIN must be {PIN_LENGTH} digits.", "invalid_request", "pin")
    return value


def hash_pin(pin: str, salt: str | None = None, iterations: int = PIN_ITERATIONS) -> tuple[str, str, int]:
    """Return (hash, salt, iterations). The salt is new unless one is supplied."""
    salt = salt or secrets.token_hex(SALT_BYTES)
    digest = hashlib.pbkdf2_hmac("sha256", pin.encode(), bytes.fromhex(salt), iterations)
    return digest.hex(), salt, iterations


def pin_matches(pin: str, pin_hash: str, salt: str, iterations: int) -> bool:
    candidate, _, _ = hash_pin(pin, salt, iterations)
    return hmac.compare_digest(candidate, pin_hash)


def new_session_token() -> tuple[str, str, datetime]:
    """Return (token for the cookie, its hash for storage, expiry)."""
    token = secrets.token_urlsafe(TOKEN_BYTES)
    return token, hash_token(token), datetime.now(timezone.utc) + SESSION_LIFETIME


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def lockout_until(failed_attempts: int) -> datetime | None:
    """When an account should stay locked after this many consecutive failures."""
    if failed_attempts < MAX_FAILED_ATTEMPTS:
        return None
    return datetime.now(timezone.utc) + LOCKOUT
