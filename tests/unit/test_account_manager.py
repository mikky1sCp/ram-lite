from __future__ import annotations
import os
import tempfile
import unittest
from unittest.mock import patch

from classes.account_manager import AccountManager
from classes.operation_result import OperationResult


class AccountManagerTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.manager = AccountManager(data_dir=self.folder.name)

    def _import(self, cookie: str, info=("alice", 123), validation=None):
        if validation is None:
            validation = OperationResult.success()
        with patch("classes.account_manager.RobloxAPI.get_user_info_from_api",
                   return_value=info), \
             patch("classes.account_manager.RobloxAPI.validate_cookie",
                   return_value=validation):
            return self.manager.import_cookie_account_result(cookie)

    def test_empty_cookie_rejected(self):
        result = self.manager.import_cookie_account_result("")
        self.assertFalse(result)
        self.assertEqual(result.code, "COOKIE_MISSING")

    def test_invalid_cookie_rejected(self):
        result = self._import("bad", info=None)
        self.assertFalse(result)
        self.assertEqual(result.code, "COOKIE_INVALID")

    def test_successful_import_adds_account_and_saves(self):
        result = self._import("good")
        self.assertTrue(result)
        self.assertIn("alice", self.manager.accounts)
        self.assertEqual(self.manager.accounts["alice"]["user_id"], 123)
        self.assertTrue(os.path.isfile(self.manager.accounts_file))

    def test_import_preserves_existing_note(self):
        self._import("good")
        self.manager.set_note("alice", "main")
        self._import("good")
        self.assertEqual(self.manager.get_note("alice"), "main")

    def test_delete_account(self):
        self._import("good")
        self.assertTrue(self.manager.delete_account("alice"))
        self.assertNotIn("alice", self.manager.accounts)
        self.assertFalse(self.manager.delete_account("missing"))

    def test_persistence_across_instances(self):
        self._import("good")
        reloaded = AccountManager(data_dir=self.folder.name)
        self.assertIn("alice", reloaded.accounts)
        self.assertEqual(reloaded.accounts["alice"]["cookie"], "good")

    def test_set_note_persists(self):
        self._import("good")
        self.assertTrue(self.manager.set_note("alice", "main"))
        self.assertEqual(self.manager.get_note("alice"), "main")
        reloaded = AccountManager(data_dir=self.folder.name)
        self.assertEqual(reloaded.get_note("alice"), "main")

    def test_set_note_missing_account_returns_false(self):
        self.assertFalse(self.manager.set_note("missing", "x"))


if __name__ == "__main__":
    unittest.main()