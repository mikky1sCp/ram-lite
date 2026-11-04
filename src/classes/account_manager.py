from __future__ import annotations

import json
import os
import threading
import time

from classes.operation_result import OperationResult
from classes.roblox_api import RobloxAPI
from utils.app_paths import get_data_dir
from utils.atomic_io import write_json_atomic


class AccountManager:
    """Stores accounts and handles the cookie-import workflow."""

    def __init__(self, data_dir: str | None = None):
        self.data_dir = data_dir or get_data_dir()
        os.makedirs(self.data_dir, exist_ok=True)
        self.accounts_file = os.path.join(self.data_dir, "accounts.json")
        self._lock = threading.RLock()
        self.accounts: dict[str, dict] = self._load()

    def _load(self) -> dict:
        try:
            with open(self.accounts_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            pass
        return {}

    def save_accounts(self) -> None:
        with self._lock:
            write_json_atomic(
                self.accounts_file, self.accounts,
                prefix=".accounts.", fsync=True,
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

    def set_note(self, username: str, note: str) -> bool:
        with self._lock:
            if username not in self.accounts:
                return False
            self.accounts[username]["note"] = note
            self.save_accounts()
            return True

    def get_note(self, username: str) -> str:
        return self.accounts.get(username, {}).get("note", "")