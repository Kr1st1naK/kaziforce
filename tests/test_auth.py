"""PIN hashing, phone normalisation and session tokens (no database needed)."""

from datetime import datetime, timezone

import pytest

from kaziforce_api.auth import (
    MAX_FAILED_ATTEMPTS,
    PIN_ITERATIONS,
    AuthError,
    check_pin,
    check_role,
    hash_pin,
    hash_token,
    local_phone,
    lockout_until,
    new_session_token,
    normalise_phone,
    pin_matches,
)

FAST = 1  # one iteration: these tests check the algorithm, not its cost


@pytest.mark.parametrize("typed", ["712345678", "0712345678", "254712345678", "+254 712 345 678", "0712 345 678"])
def test_every_way_of_writing_one_number_normalises_to_the_same_account(typed):
    assert normalise_phone(typed) == "254712345678"
    assert local_phone(normalise_phone(typed)) == "712345678"


@pytest.mark.parametrize("bad", ["", "71234", "0712345678912345", "abc", None])
def test_an_unusable_phone_number_is_refused(bad):
    with pytest.raises(AuthError) as caught:
        normalise_phone(bad)
    assert caught.value.field == "phone"


@pytest.mark.parametrize("bad", ["123", "12345", "12a4", "", None, 1234])
def test_a_pin_must_be_four_digits(bad):
    with pytest.raises(AuthError) as caught:
        check_pin(bad)
    assert caught.value.field == "pin"


def test_role_must_be_worker_or_client():
    assert check_role("worker") == "worker" and check_role("client") == "client"
    with pytest.raises(AuthError):
        check_role("admin")


def test_the_pin_is_never_recoverable_from_what_is_stored():
    pin_hash, salt, iterations = hash_pin("1234", iterations=FAST)
    assert "1234" not in pin_hash and "1234" not in salt
    assert iterations == FAST and len(bytes.fromhex(pin_hash)) == 32


def test_the_same_pin_hashes_differently_for_two_accounts():
    first, salt_a, _ = hash_pin("1234", iterations=FAST)
    second, salt_b, _ = hash_pin("1234", iterations=FAST)
    assert salt_a != salt_b and first != second


def test_a_pin_verifies_only_against_its_own_salt():
    pin_hash, salt, iterations = hash_pin("4321", iterations=FAST)
    assert pin_matches("4321", pin_hash, salt, iterations)
    assert not pin_matches("1234", pin_hash, salt, iterations)
    _, other_salt, _ = hash_pin("4321", iterations=FAST)
    assert not pin_matches("4321", pin_hash, other_salt, iterations)


def test_the_default_iteration_count_is_not_weakened():
    assert PIN_ITERATIONS >= 600_000


def test_a_session_token_is_stored_only_as_a_hash():
    token, token_hash, expires_at = new_session_token()
    assert len(token) >= 32 and token != token_hash
    assert hash_token(token) == token_hash and len(token_hash) == 64
    assert expires_at > datetime.now(timezone.utc)
    assert new_session_token()[0] != token  # a fresh token every time


def test_an_account_locks_only_after_repeated_failures():
    assert lockout_until(MAX_FAILED_ATTEMPTS - 1) is None
    assert lockout_until(MAX_FAILED_ATTEMPTS) is not None
