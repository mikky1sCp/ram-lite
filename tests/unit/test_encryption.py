from __future__ import annotations
import base64
import json
import os
import tempfile
import unittest

from classes.encryption import (
    EncryptedDataError,
    EncryptionConfig,
    PasswordDecryptionError,
    PasswordEncryption,
)


class RoundtripTests(unittest.TestCase):
    def test_dict_roundtrip(self):
        enc = PasswordEncryption("hunter2hunter2")
        payload = enc.encrypt_data({"alice": {"cookie": "x"}})
        dec = PasswordEncryption("hunter2hunter2", enc.salt)
        self.assertEqual(dec.decrypt_data(payload), {"alice": {"cookie": "x"}})

    def test_wrong_password_raises(self):
        enc = PasswordEncryption("hunter2hunter2")
        payload = enc.encrypt_data({"alice": 1})
        dec = PasswordEncryption("wrong-password", enc.salt)
        with self.assertRaises(PasswordDecryptionError):
            dec.decrypt_data(payload)

    def test_tampered_ciphertext_raises(self):
        enc = PasswordEncryption("hunter2hunter2")
        payload = enc.encrypt_data({"alice": 1})
        raw = base64.b64decode(payload["ciphertext"])
        tampered = raw[:-1] + bytes([raw[-1] ^ 0xFF])
        payload["ciphertext"] = base64.b64encode(tampered).decode("ascii")
        dec = PasswordEncryption("hunter2hunter2", enc.salt)
        with self.assertRaises(PasswordDecryptionError):
            dec.decrypt_data(payload)

    def test_missing_fields_raise(self):
        enc = PasswordEncryption("hunter2hunter2")
        with self.assertRaises(EncryptedDataError):
            enc.decrypt_data({"nonce": "abc"})

    def test_salt_is_persisted(self):
        enc = PasswordEncryption("hunter2hunter2")
        salt_b64 = enc.get_salt_b64()
        self.assertEqual(
            base64.b64decode(salt_b64), enc.salt,
        )


class EncryptionConfigTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = os.path.join(self.folder.name, "encryption_config.json")

    def test_disabled_by_default(self):
        cfg = EncryptionConfig(self.path)
        self.assertFalse(cfg.is_enabled())
        self.assertIsNone(cfg.get_salt())

    def test_enable_persists(self):
        cfg = EncryptionConfig(self.path)
        cfg.enable(base64.b64encode(b"x" * 32).decode("ascii"))
        self.assertTrue(cfg.is_enabled())
        again = EncryptionConfig(self.path)
        self.assertTrue(again.is_enabled())
        self.assertEqual(again.get_salt(), b"x" * 32)

    def test_disable_persists(self):
        cfg = EncryptionConfig(self.path)
        cfg.enable(base64.b64encode(b"x" * 32).decode("ascii"))
        cfg.disable()
        self.assertFalse(cfg.is_enabled())
        again = EncryptionConfig(self.path)
        self.assertFalse(again.is_enabled())


if __name__ == "__main__":
    unittest.main()