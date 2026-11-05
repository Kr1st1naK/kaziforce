"""Field encryption: AES-256-GCM round trips, tamper and wrong-key detection, the phone hash, and key loading."""

import base64
import logging

import pytest

from kaziforce_api.crypto import (
    FIRST_NAME,
    PHONE,
    ConfigError,
    CryptoError,
    FieldCipher,
    FieldCrypto,
    generate_key,
    is_production,
    load_from_env,
)

PHONE_NUMBER = "254712345678"


def key() -> bytes:
    return base64.urlsafe_b64decode(generate_key())


@pytest.fixture
def cipher() -> FieldCipher:
    return FieldCipher({"v1": key()})


def test_a_value_survives_a_round_trip(cipher):
    assert cipher.decrypt(cipher.encrypt(PHONE_NUMBER, PHONE), PHONE) == PHONE_NUMBER


def test_non_ascii_names_survive_a_round_trip(cipher):
    assert cipher.decrypt(cipher.encrypt("Wanjiru Njoroge-Müller", FIRST_NAME), FIRST_NAME) == "Wanjiru Njoroge-Müller"


def test_the_stored_form_is_versioned_and_hides_the_value(cipher):
    token = cipher.encrypt(PHONE_NUMBER, PHONE)
    assert token.startswith("v1:")
    assert PHONE_NUMBER not in token and "712345678" not in token


def test_the_same_value_encrypts_differently_each_time(cipher):
    # A fresh random nonce per value: two equal numbers cannot be recognised as equal.
    assert cipher.encrypt(PHONE_NUMBER, PHONE) != cipher.encrypt(PHONE_NUMBER, PHONE)


def test_an_altered_value_is_detected(cipher):
    token = cipher.encrypt(PHONE_NUMBER, PHONE)
    head, body = token.split(":", 1)
    raw = bytearray(base64.urlsafe_b64decode(body))
    raw[-1] ^= 0x01  # one bit of the authentication tag
    with pytest.raises(CryptoError):
        cipher.decrypt(f"{head}:{base64.urlsafe_b64encode(bytes(raw)).decode()}", PHONE)
    raw[-1] ^= 0x01
    raw[14] ^= 0x01  # one bit of the ciphertext
    with pytest.raises(CryptoError):
        cipher.decrypt(f"{head}:{base64.urlsafe_b64encode(bytes(raw)).decode()}", PHONE)


def test_the_wrong_key_fails(cipher):
    token = cipher.encrypt(PHONE_NUMBER, PHONE)
    with pytest.raises(CryptoError):
        FieldCipher({"v1": key()}).decrypt(token, PHONE)


def test_a_value_moved_to_another_column_fails(cipher):
    with pytest.raises(CryptoError):
        cipher.decrypt(cipher.encrypt(PHONE_NUMBER, PHONE), FIRST_NAME)


@pytest.mark.parametrize("bad", ["", "v1", "v1:", "v1:not base64!", "v9:AAAA", "plain text", "v1:AAAA"])
def test_a_malformed_value_is_refused(cipher, bad):
    with pytest.raises(CryptoError):
        cipher.decrypt(bad, PHONE)


def test_an_old_key_version_still_reads_after_a_new_one_is_added():
    old, new = key(), key()
    before = FieldCipher({"v1": old}).encrypt(PHONE_NUMBER, PHONE)
    rotated = FieldCipher({"v1": old, "v2": new}, current="v2")
    assert rotated.decrypt(before, PHONE) == PHONE_NUMBER
    assert rotated.encrypt(PHONE_NUMBER, PHONE).startswith("v2:")


def test_a_key_of_the_wrong_length_is_refused():
    with pytest.raises(ConfigError):
        FieldCipher({"v1": b"too short"})


def test_the_error_never_contains_the_value(cipher):
    token = cipher.encrypt(PHONE_NUMBER, PHONE)
    with pytest.raises(CryptoError) as caught:
        FieldCipher({"v1": key()}).decrypt(token, PHONE)
    assert PHONE_NUMBER not in str(caught.value) and token not in str(caught.value)


# The phone hash

def crypto(hmac_key: bytes | None = None) -> FieldCrypto:
    return FieldCrypto(FieldCipher({"v1": key()}), hmac_key or key())


def test_the_phone_hash_is_stable_and_64_hex_characters():
    c = crypto()
    assert c.phone_hash(PHONE_NUMBER) == c.phone_hash(PHONE_NUMBER)
    assert len(c.phone_hash(PHONE_NUMBER)) == 64 and int(c.phone_hash(PHONE_NUMBER), 16) >= 0


def test_the_phone_hash_depends_on_the_secret_and_on_the_number():
    hmac_key = key()
    assert crypto(hmac_key).phone_hash(PHONE_NUMBER) == crypto(hmac_key).phone_hash(PHONE_NUMBER)
    assert crypto().phone_hash(PHONE_NUMBER) != crypto().phone_hash(PHONE_NUMBER)
    assert crypto(hmac_key).phone_hash(PHONE_NUMBER) != crypto(hmac_key).phone_hash("254712345679")


def test_the_phone_hash_is_not_a_plain_hash_of_the_number():
    import hashlib

    assert crypto().phone_hash(PHONE_NUMBER) != hashlib.sha256(PHONE_NUMBER.encode()).hexdigest()


# Loading the keys

GOOD = {"KAZIFORCE_FIELD_KEY": generate_key(), "KAZIFORCE_PHONE_HMAC_KEY": generate_key()}


def test_keys_load_from_the_environment():
    c = load_from_env({**GOOD, "KAZIFORCE_ENV": "production"})
    assert c.cipher.decrypt(c.cipher.encrypt("x", PHONE), PHONE) == "x"


@pytest.mark.parametrize("env", [{}, {"KAZIFORCE_ENV": "production"}, {"KAZIFORCE_ENV": "staging"}, {"FLASK_ENV": "production"}])
def test_it_refuses_to_start_outside_development_without_keys(env):
    with pytest.raises(ConfigError) as caught:
        load_from_env(env)
    assert "KAZIFORCE_FIELD_KEY" in str(caught.value) and "python -m kaziforce_api.crypto" in str(caught.value)


def test_one_missing_key_is_enough_to_refuse_in_production():
    with pytest.raises(ConfigError) as caught:
        load_from_env({"KAZIFORCE_ENV": "production", "KAZIFORCE_FIELD_KEY": GOOD["KAZIFORCE_FIELD_KEY"]})
    assert "KAZIFORCE_PHONE_HMAC_KEY" in str(caught.value)


def test_nothing_set_means_production():
    assert is_production({}) and not is_production({"KAZIFORCE_ENV": "development"})
    assert not is_production({"FLASK_ENV": "development"}) and not is_production({"KAZIFORCE_ENV": "test"})


def test_development_runs_without_keys_but_says_so(caplog):
    with caplog.at_level(logging.WARNING):
        c = load_from_env({"KAZIFORCE_ENV": "development"})
    assert c.cipher.decrypt(c.cipher.encrypt("x", PHONE), PHONE) == "x"
    assert "development key" in caplog.text


@pytest.mark.parametrize("bad", ["not base64 !!", base64.urlsafe_b64encode(b"short").decode()])
def test_a_malformed_key_is_refused_without_echoing_it(bad):
    with pytest.raises(ConfigError) as caught:
        load_from_env({**GOOD, "KAZIFORCE_ENV": "production", "KAZIFORCE_FIELD_KEY": bad})
    assert bad not in str(caught.value)


def test_a_field_key_longer_than_32_bytes_is_refused():
    long_key = base64.urlsafe_b64encode(b"x" * 48).decode()
    with pytest.raises(ConfigError):
        load_from_env({**GOOD, "KAZIFORCE_ENV": "production", "KAZIFORCE_FIELD_KEY": long_key})


def test_generated_keys_are_32_random_bytes():
    assert len(base64.urlsafe_b64decode(generate_key())) == 32
    assert generate_key() != generate_key()
