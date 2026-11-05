"""
Application-level encryption for the fields that identify a person: a phone number and a name.

Nothing here is a cipher of our own. Encryption is AES-256-GCM from the `cryptography`
package; the lookup hash is HMAC-SHA256 from the standard library.

**What is stored.** A value is stored as `v1:<base64url(nonce || ciphertext || tag)>`. The nonce
is 12 random bytes, fresh for every value, so the same phone number encrypts differently each
time. The `v1` prefix names the key that encrypted it, so a later key can be introduced and old
values still read (rotation needs a re-encrypting script, which does not exist yet; see
docs/privacy-and-keys.md). The *purpose* of the field ("account.phone") is passed as GCM's
associated data, so a ciphertext copied from one column into another fails to decrypt.

**Why a second key.** The phone number is the sign-in lookup key, and a ciphertext with a random
nonce cannot be looked up. `phone_hash` is HMAC-SHA256 of the normalised number under a separate
secret, so a database copy does not allow the (small) Kenyan number space to be enumerated into
hashes without that secret.

**Where the keys live.** In the server's environment (KAZIFORCE_FIELD_KEY,
KAZIFORCE_PHONE_HMAC_KEY), not in the database or the repository. That is only as strong as the
server: there is no KMS and no automated rotation (docs/limitations.md).

Nothing in this module logs, and no error message contains a plaintext, a ciphertext or a key.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import logging
import os
import secrets
from collections.abc import Mapping
from dataclasses import dataclass

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

log = logging.getLogger(__name__)

CURRENT_VERSION = "v1"
KEY_BYTES = 32  # AES-256
NONCE_BYTES = 12  # the size GCM is specified for
MIN_HMAC_KEY_BYTES = 32

FIELD_KEY_VAR = "KAZIFORCE_FIELD_KEY"
PHONE_HMAC_KEY_VAR = "KAZIFORCE_PHONE_HMAC_KEY"
ENV_VAR = "KAZIFORCE_ENV"

# Only a named development or test environment may start without keys. Anything else, including
# no setting at all, is treated as production.
DEV_ENVIRONMENTS = ("development", "test")

# Purposes bound into the ciphertext.
PHONE = "account.phone"
FIRST_NAME = "account.first_name"
LAST_NAME = "account.last_name"


class CryptoError(Exception):
    """A value could not be encrypted or decrypted. The message never contains the value."""


class ConfigError(RuntimeError):
    """The keys are missing or malformed. Raised at start-up so the app refuses to run."""


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii")


def _b64decode(text: str) -> bytes:
    try:
        return base64.urlsafe_b64decode(text.encode("ascii"))
    except (binascii.Error, UnicodeEncodeError, ValueError) as exc:
        raise CryptoError("the stored value is not valid base64") from exc


class FieldCipher:
    """AES-256-GCM with a random nonce per value and a key-version prefix."""

    def __init__(self, keys: Mapping[str, bytes], current: str = CURRENT_VERSION):
        if current not in keys:
            raise ConfigError(f"no key for the current version {current!r}")
        for version, key in keys.items():
            if len(key) != KEY_BYTES:
                raise ConfigError(f"the {version} field key must be {KEY_BYTES} bytes")
        self._keys = dict(keys)
        self._current = current

    def encrypt(self, plaintext: str, purpose: str) -> str:
        nonce = os.urandom(NONCE_BYTES)
        sealed = AESGCM(self._keys[self._current]).encrypt(nonce, plaintext.encode("utf-8"), purpose.encode("ascii"))
        return f"{self._current}:{_b64encode(nonce + sealed)}"

    def decrypt(self, token: str, purpose: str) -> str:
        version, separator, body = (token or "").partition(":")
        key = self._keys.get(version)
        if not separator or key is None:
            raise CryptoError("the stored value has an unknown key version")
        raw = _b64decode(body)
        if len(raw) <= NONCE_BYTES:
            raise CryptoError("the stored value is too short")
        try:
            return AESGCM(key).decrypt(raw[:NONCE_BYTES], raw[NONCE_BYTES:], purpose.encode("ascii")).decode("utf-8")
        except (InvalidTag, UnicodeDecodeError) as exc:
            # One message for a wrong key, an altered value and a value from another column:
            # telling them apart would only help someone probing the database.
            raise CryptoError("the stored value could not be decrypted: wrong key or altered data") from exc


@dataclass(frozen=True)
class FieldCrypto:
    """The cipher for stored values and the keyed hash for looking a phone number up."""

    cipher: FieldCipher
    phone_hmac_key: bytes

    def phone_hash(self, phone: str) -> str:
        """HMAC-SHA256 of a normalised phone number, as 64 hex characters."""
        return hmac.new(self.phone_hmac_key, phone.encode("ascii"), hashlib.sha256).hexdigest()

    def encrypt_phone(self, phone: str) -> str:
        return self.cipher.encrypt(phone, PHONE)

    def decrypt_phone(self, token: str) -> str:
        return self.cipher.decrypt(token, PHONE)

    def encrypt_name(self, name: str, purpose: str) -> str:
        return self.cipher.encrypt(name, purpose)

    def decrypt_name(self, token: str, purpose: str) -> str:
        return self.cipher.decrypt(token, purpose)


def generate_key() -> str:
    """A fresh 32-byte key as URL-safe base64, for a .env file."""
    return _b64encode(secrets.token_bytes(KEY_BYTES))


def environment(env: Mapping[str, str] | None = None) -> str:
    env = os.environ if env is None else env
    return (env.get(ENV_VAR) or env.get("FLASK_ENV") or "production").strip().lower()


def is_production(env: Mapping[str, str] | None = None) -> bool:
    return environment(env) not in DEV_ENVIRONMENTS


def _decode_key(name: str, value: str, minimum: int) -> bytes:
    try:
        key = base64.urlsafe_b64decode(value.strip().encode("ascii"))
    except (binascii.Error, UnicodeEncodeError, ValueError) as exc:
        raise ConfigError(f"{name} is not valid URL-safe base64. Generate one with: python -m kaziforce_api.crypto") from exc
    if len(key) < minimum:
        raise ConfigError(f"{name} must decode to at least {minimum} bytes. Generate one with: python -m kaziforce_api.crypto")
    return key


def _dev_key(label: str) -> bytes:
    # Not a secret: it is in the source. It lets a development machine run without setup, and
    # `load_from_env` says so loudly each time it is used.
    return hashlib.sha256(f"kaziforce-insecure-development-key:{label}".encode()).digest()


def load_from_env(env: Mapping[str, str] | None = None) -> FieldCrypto:
    """Build the keys from the environment, or refuse.

    In production (anything but KAZIFORCE_ENV / FLASK_ENV set to development or test) both keys
    are required. In development a missing key falls back to a fixed, public one with a warning,
    which protects nothing and is there so a fresh checkout runs.
    """
    env = os.environ if env is None else env
    field_value, hmac_value = env.get(FIELD_KEY_VAR, "").strip(), env.get(PHONE_HMAC_KEY_VAR, "").strip()
    missing = [name for name, value in ((FIELD_KEY_VAR, field_value), (PHONE_HMAC_KEY_VAR, hmac_value)) if not value]

    if missing and is_production(env):
        raise ConfigError(
            f"{' and '.join(missing)} must be set outside development. "
            "Generate each with: python -m kaziforce_api.crypto"
        )
    if missing:
        log.warning("%s not set: using the public development key, which protects nothing", " and ".join(missing))

    field_key = _decode_key(FIELD_KEY_VAR, field_value, KEY_BYTES) if field_value else _dev_key("field")
    if len(field_key) != KEY_BYTES:
        raise ConfigError(f"{FIELD_KEY_VAR} must decode to exactly {KEY_BYTES} bytes. Generate one with: python -m kaziforce_api.crypto")
    hmac_key = _decode_key(PHONE_HMAC_KEY_VAR, hmac_value, MIN_HMAC_KEY_BYTES) if hmac_value else _dev_key("phone")
    return FieldCrypto(FieldCipher({CURRENT_VERSION: field_key}), hmac_key)


if __name__ == "__main__":
    print(f"{FIELD_KEY_VAR}={generate_key()}")
    print(f"{PHONE_HMAC_KEY_VAR}={generate_key()}")
