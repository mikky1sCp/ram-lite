from __future__ import annotations

import json
import os
import threading
import time

from classes.encryption import (
    EncryptionConfig,
    EncryptedDataError,
    PasswordDecryptionError,
    PasswordEncryption,
)
from classes.operation_result import OperationResult
from classes.roblox_api import RobloxAPI
from utils.app_paths import get_data_dir
from utils.atomic_io import write_json_atomic


class AccountManagerError(Exception):
    pass


class PasswordRequiredError(AccountManagerError):
    pass


class AccountPasswordError(AccountManagerError):
    pass


class AccountManager:
    def __init__(self, data_dir: str | None = None, password: str | None = None):
        self.data_dir = data_dir or get_data_dir()
        os.makedirs(self.data_dir, exist_ok=True)
        self.accounts_file = os.path.join(self.data_dir, "accounts.json")
        self.encryption_config = EncryptionConfig(
            os.path.join(self.data_dir, "encryption_config.json")
        )
        self._encryptor: PasswordEncryption | None = None
        self._lock = threading.RLock()

        if self.encryption_config.is_enabled():
            if password is None:
                raise PasswordRequiredError(
                    "This accounts file is encrypted. A password is required."
                )
            salt = self.encryption_config.get_salt()
            if salt is None:
                raise AccountManagerError(
                    "Encryption is enabled but the salt is missing."
                )
            self._encryptor = PasswordEncryption(password, salt)

        self.accounts = self._load()

    def _load(self) -> dict:
        try:
            with open(self.accounts_file, "r", encoding="utf-8") as f:
                document = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return {}
        if not isinstance(document, dict):
            return {}
        if document.get("encrypted"):
            if self._encryptor is None:
                raise PasswordRequiredError(
                    "The accounts file is encrypted but no password was provided."
                )
            try:
                data = self._encryptor.decrypt_data(document.get("data", {}))
            except PasswordDecryptionError as exc:
                raise AccountPasswordError(
                    "Wrong password or corrupted encrypted file."
                ) from exc
            except EncryptedDataError as exc:
                raise AccountManagerError(
                    f"Encrypted payload is malformed: {exc}"
                ) from exc
            result = data if isinstance(data, dict) else {}
            self._migrate(result)
            return result
        self._migrate(document)
        return document

    @staticmethod
    def _migrate(accounts: dict) -> None:
        for data in accounts.values():
            if isinstance(data, dict) and "cookie_valid" not in data:
                data["cookie_valid"] = None

    def save_accounts(self) -> None:
        with self._lock:
            if self._encryptor is not None:
                payload = self._encryptor.encrypt_data(self.accounts)
                document = {"encrypted": True, "data": payload}
            else:
                document = self.accounts
            write_json_atomic(
                self.accounts_file, document,
                prefix=".accounts.", fsync=True,
            )

    def is_encryption_enabled(self) -> bool:
        return self._encryptor is not None

    def enable_encryption(self, password: str) -> OperationResult:
        if len(password) < 8:
            return OperationResult.failure(
                "PASSWORD_TOO_SHORT", "Password Too Short",
                "Use a password with at least 8 characters.",
            )
        if self._encryptor is not None:
            return OperationResult.failure(
                "ALREADY_ENCRYPTED", "Already Encrypted",
                "Encryption is already enabled.",
            )
        try:
            encryptor = PasswordEncryption(password)
        except Exception as exc:
            return OperationResult.failure(
                "ENCRYPTION_INIT_FAILED", "Encryption Failed",
                f"Could not set up encryption: {exc}",
            )
        # Persist the salt first so a crash after re-encrypting the accounts
        # file still lets the next launch decrypt it.
        try:
            self.encryption_config.enable(encryptor.get_salt_b64())
        except Exception as exc:
            return OperationResult.failure(
                "ENCRYPTION_CONFIG_FAILED", "Encryption Failed",
                f"Could not save encryption config: {exc}",
            )
        self._encryptor = encryptor
        try:
            self.save_accounts()
        except Exception as exc:
            self._encryptor = None
            try:
                self.encryption_config.disable()
            except Exception:
                pass
            return OperationResult.failure(
                "ENCRYPTION_SAVE_FAILED", "Encryption Failed",
                f"Could not re-encrypt accounts: {exc}",
            )
        return OperationResult.success(
            "Encryption enabled. Keep this password safe — "
            "there is no recovery if you lose it."
        )

    def import_cookie_account_result(self, cookie: str) -> OperationResult:
        cookie = (cookie or "").strip()
        if not cookie:
            return OperationResult.failure(
                "COOKIE_MISSING", "Cookie Missing",
                "Paste a Roblox security cookie.",
            )
        info = RobloxAPI.get_user_info_from_api(cookie)
        if info is None:
            return OperationResult.failure(
                "COOKIE_INVALID", "Cookie Rejected",
                "Roblox did not return an account for this cookie.",
            )
        username, user_id = info
        validation = RobloxAPI.validate_cookie(cookie)
        if not validation:
            return validation
        with self._lock:
            existing_note = self.accounts.get(username, {}).get("note", "")
            self.accounts[username] = {
                "cookie": cookie,
                "user_id": user_id,
                "note": existing_note,
                "added_date": time.strftime("%Y-%m-%d %H:%M:%S"),
                "cookie_valid": True,
            }
            self.save_accounts()
        return OperationResult.success(f"Added {username}.", data=username)

    def delete_account(self, username: str) -> bool:
        with self._lock:
            if username not in self.accounts:
                return False
            del self.accounts[username]
            self.save_accounts()
            return True

    def set_cookie_status(
        self, username: str, is_valid: bool, save: bool = True,
    ) -> None:
        with self._lock:
            if username not in self.accounts:
                return
            self.accounts[username]["cookie_valid"] = is_valid
            if save:
                self.save_accounts()

    def set_note(self, username: str, note: str) -> bool:
        with self._lock:
            if username not in self.accounts:
                return False
            self.accounts[username]["note"] = note
            self.save_accounts()
            return True

    def get_note(self, username: str) -> str:
        return self.accounts.get(username, {}).get("note", "")