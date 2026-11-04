from __future__ import annotations

import base64
import binascii
import json

from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Random import get_random_bytes

PBKDF2_ITERATIONS = 200_000
SALT_BYTES = 32
KEY_LEN = 32


class EncryptionError(Exception):
    pass


class PasswordDecryptionError(EncryptionError):
    pass


class EncryptedDataError(EncryptionError):
    pass


def _decode(package: dict) -> tuple[bytes, bytes, bytes]:
    if not isinstance(package, dict):
        raise EncryptedDataError("Encrypted payload is not an object.")
    required = ("nonce", "tag", "ciphertext")
    if any(not isinstance(package.get(k), str) for k in required):
        raise EncryptedDataError("Encrypted payload is missing required fields.")
    try:
        return tuple(
            base64.b64decode(package[k], validate=True) for k in required
        )
    except (ValueError, TypeError, binascii.Error) as exc:
        raise EncryptedDataError(
            "Encrypted payload contains invalid encoded data."
        ) from exc


class PasswordEncryption:
    def __init__(self, password: str, salt: bytes | None = None):
        if not password:
            raise ValueError("Password must not be empty.")
        self.salt = salt if salt is not None else get_random_bytes(SALT_BYTES)
        self._key = PBKDF2(
            password.encode("utf-8"),
            self.salt,
            dkLen=KEY_LEN,
            count=PBKDF2_ITERATIONS,
        )

    def get_salt_b64(self) -> str:
        return base64.b64encode(self.salt).decode("ascii")

    def encrypt_data(self, data) -> dict:
        if isinstance(data, dict):
            data = json.dumps(data, ensure_ascii=False)
        if isinstance(data, str):
            data = data.encode("utf-8")
        cipher = AES.new(self._key, AES.MODE_GCM)
        ciphertext, tag = cipher.encrypt_and_digest(data)
        return {
            "nonce": base64.b64encode(cipher.nonce).decode("ascii"),
            "tag": base64.b64encode(tag).decode("ascii"),
            "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
        }

    def decrypt_data(self, package: dict):
        nonce, tag, ciphertext = _decode(package)
        try:
            cipher = AES.new(self._key, AES.MODE_GCM, nonce=nonce)
            plaintext = cipher.decrypt_and_verify(ciphertext, tag)
        except (ValueError, KeyError) as exc:
            raise PasswordDecryptionError(
                "The password did not decrypt this data."
            ) from exc
        try:
            return json.loads(plaintext.decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as exc:
            raise EncryptedDataError(
                "The decrypted payload is not valid JSON."
            ) from exc


class EncryptionConfig:
    def __init__(self, path: str):
        self.path = path
        self._data: dict = self._read()

    def _read(self) -> dict:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return {}

    def save(self) -> None:
        from utils.atomic_io import write_json_atomic
        write_json_atomic(
            self.path, self._data, prefix=".encryption.", fsync=True,
        )

    def is_enabled(self) -> bool:
        return bool(self._data.get("encrypted"))

    def get_salt(self) -> bytes | None:
        salt = self._data.get("salt")
        if not isinstance(salt, str):
            return None
        try:
            return base64.b64decode(salt, validate=True)
        except (ValueError, binascii.Error):
            return None

    def enable(self, salt_b64: str) -> None:
        self._data = {"encrypted": True, "salt": salt_b64, "version": 1}
        self.save()

    def disable(self) -> None:
        self._data = {"encrypted": False}
        self.save()