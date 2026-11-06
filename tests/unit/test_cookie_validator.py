from __future__ import annotations
import os
import tempfile
import threading
import unittest
from unittest.mock import patch

from classes.account_manager import AccountManager
from classes.operation_result import OperationResult
from features.cookie_validator import validate_all_cookies


def _seed(manager, accounts: dict[str, dict]) -> None:
    manager.accounts.update(accounts)
    manager.save_accounts()


def _account(user_id: int, cookie: str = "c") -> dict:
    return {
        "cookie": cookie,
        "user_id": user_id,
        "note": "",
        "added_date": "2025-01-01 00:00:00",
        "cookie_valid": None,
    }


class ValidateAllCookiesTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.manager = AccountManager(data_dir=self.folder.name)

    def test_all_valid(self):
        _seed(self.manager, {
            "alice": _account(1),
            "bob": _account(2),
        })
        seen = []
        done = []
        with patch(
            "features.cookie_validator.RobloxAPI.validate_cookie",
            return_value=OperationResult.success(),
        ):
            validate_all_cookies(
                self.manager,
                on_progress=lambda u, v: seen.append((u, v)),
                on_done=lambda v, i: done.append((v, i)),
                delay=0,
            )
        self.assertEqual(done, [(2, 0)])
        self.assertEqual([v for _, v in seen], [True, True])
        self.assertEqual(
            self.manager.accounts["alice"]["cookie_valid"], True,
        )

    def test_some_invalid(self):
        _seed(self.manager, {
            "alice": _account(1),
            "bob": _account(2),
        })
        results = [
            OperationResult.success(),
            OperationResult.failure(
                "COOKIE_INVALID", "Rejected", "Bad cookie.",
            ),
        ]
        seen = []
        done = []
        with patch(
            "features.cookie_validator.RobloxAPI.validate_cookie",
            side_effect=results,
        ):
            validate_all_cookies(
                self.manager,
                on_progress=lambda u, v: seen.append((u, v)),
                on_done=lambda v, i: done.append((v, i)),
                delay=0,
            )
        self.assertEqual(done, [(1, 1)])
        self.assertEqual(seen, [("alice", True), ("bob", False)])
        self.assertFalse(
            self.manager.accounts["bob"]["cookie_valid"],
        )

    def test_network_error_leaves_status_untouched(self):
        _seed(self.manager, {"alice": _account(1)})
        self.manager.accounts["alice"]["cookie_valid"] = True
        done = []
        with patch(
            "features.cookie_validator.RobloxAPI.validate_cookie",
            return_value=OperationResult.failure(
                "NETWORK_ERROR", "Network", "Offline.",
            ),
        ):
            validate_all_cookies(
                self.manager,
                on_progress=lambda u, v: None,
                on_done=lambda v, i: done.append((v, i)),
                delay=0,
            )
        self.assertEqual(done, [(0, 0)])
        self.assertTrue(
            self.manager.accounts["alice"]["cookie_valid"],
        )

    def test_stop_event_halts_early(self):
        _seed(self.manager, {
            "a": _account(1),
            "b": _account(2),
            "c": _account(3),
        })
        stop = threading.Event()
        seen = []
        def progress(username, is_valid):
            seen.append(username)
            stop.set()
        with patch(
            "features.cookie_validator.RobloxAPI.validate_cookie",
            return_value=OperationResult.success(),
        ):
            validate_all_cookies(
                self.manager,
                on_progress=progress,
                on_done=lambda v, i: None,
                delay=0,
                stop_event=stop,
            )
        self.assertEqual(len(seen), 1)

    def test_empty_manager_does_not_fail(self):
        done = []
        with patch(
            "features.cookie_validator.RobloxAPI.validate_cookie",
        ) as mock:
            validate_all_cookies(
                self.manager,
                on_progress=lambda u, v: None,
                on_done=lambda v, i: done.append((v, i)),
                delay=0,
            )
        mock.assert_not_called()
        self.assertEqual(done, [(0, 0)])


if __name__ == "__main__":
    unittest.main()