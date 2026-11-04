from __future__ import annotations
import unittest
from unittest.mock import patch

from classes.operation_result import OperationResult
from features import launcher


class BuildUrlTests(unittest.TestCase):
    def test_home_url_contains_ticket_and_tracker(self):
        url = launcher.build_home_url("TICKET")
        self.assertTrue(url.startswith("roblox-player:1+launchmode:play"))
        self.assertIn("gameinfo:TICKET", url)
        self.assertIn("browsertrackerid:", url)

    def test_place_url_includes_place_id(self):
        url = launcher.build_place_url("TICKET", "12345")
        self.assertIn("placeId=12345", url)
        self.assertIn("gameinfo:TICKET", url)


class LaunchTests(unittest.TestCase):
    def test_invalid_place_id_returns_error(self):
        result = launcher.launch_place({"cookie": "x"}, "abc")
        self.assertFalse(result)
        self.assertEqual(result.code, "PLACE_ID_INVALID")

    def test_ticket_failure_propagates(self):
        failure = OperationResult.failure("COOKIE_INVALID", "Rejected", "Bad cookie.")
        with patch("features.launcher.RobloxAPI.get_auth_ticket",
                   return_value=failure), \
             patch("features.launcher.os.startfile") as start:
            result = launcher.launch_home({"cookie": "x"})
        self.assertFalse(result)
        self.assertEqual(result.code, "COOKIE_INVALID")
        start.assert_not_called()

    def test_successful_home_launch_calls_startfile(self):
        ticket = OperationResult.success(data="T1")
        with patch("features.launcher.RobloxAPI.get_auth_ticket",
                   return_value=ticket), \
             patch("features.launcher.os.startfile") as start:
            result = launcher.launch_home({"cookie": "x"})
        self.assertTrue(result)
        start.assert_called_once()
        url = start.call_args.args[0]
        self.assertIn("gameinfo:T1", url)

    def test_successful_place_launch_calls_startfile(self):
        ticket = OperationResult.success(data="T1")
        with patch("features.launcher.RobloxAPI.get_auth_ticket",
                   return_value=ticket), \
             patch("features.launcher.os.startfile") as start:
            result = launcher.launch_place({"cookie": "x"}, "12345")
        self.assertTrue(result)
        start.assert_called_once()
        url = start.call_args.args[0]
        self.assertIn("placeId=12345", url)

    def test_startfile_oserror_returns_launch_failed(self):
        ticket = OperationResult.success(data="T1")
        with patch("features.launcher.RobloxAPI.get_auth_ticket",
                   return_value=ticket), \
             patch("features.launcher.os.startfile",
                   side_effect=OSError("no handler")):
            result = launcher.launch_home({"cookie": "x"})
        self.assertFalse(result)
        self.assertEqual(result.code, "LAUNCH_FAILED")

    def test_non_default_launcher_rejected(self):
        ticket = OperationResult.success(data="T1")
        with patch("features.launcher.RobloxAPI.get_auth_ticket",
                   return_value=ticket), \
             patch("features.launcher.settings_store.get",
                   return_value="unknown_launcher"), \
             patch("features.launcher.os.startfile") as start:
            result = launcher.launch_home({"cookie": "x"})
        self.assertFalse(result)
        self.assertEqual(result.code, "LAUNCHER_UNSUPPORTED")
        start.assert_not_called()

class LauncherSelectionTests(unittest.TestCase):
    def test_bloxstrap_missing_returns_not_installed(self):
        ticket = OperationResult.success(data="T1")
        with patch("features.launcher.RobloxAPI.get_auth_ticket",
                   return_value=ticket), \
             patch("features.launcher.settings_store.get",
                   return_value="bloxstrap"), \
             patch("features.launcher.os.getenv",
                   return_value=r"C:\fake\missing"):
            result = launcher.launch_home({"cookie": "x"})
        self.assertFalse(result)
        self.assertEqual(result.code, "BLOXSTRAP_NOT_INSTALLED")

    def test_client_missing_returns_not_installed(self):
        ticket = OperationResult.success(data="T1")
        with patch("features.launcher.RobloxAPI.get_auth_ticket",
                   return_value=ticket), \
             patch("features.launcher.settings_store.get",
                   return_value="client"), \
             patch("features.launcher.os.getenv",
                   return_value=r"C:\fake\missing"):
            result = launcher.launch_home({"cookie": "x"})
        self.assertFalse(result)
        self.assertEqual(result.code, "ROBLOX_NOT_INSTALLED")

    def test_unknown_launcher_returns_unsupported(self):
        ticket = OperationResult.success(data="T1")
        with patch("features.launcher.RobloxAPI.get_auth_ticket",
                   return_value=ticket), \
             patch("features.launcher.settings_store.get",
                   return_value="unknown"):
            result = launcher.launch_home({"cookie": "x"})
        self.assertEqual(result.code, "LAUNCHER_UNSUPPORTED")


class BatchLaunchTests(unittest.TestCase):
    def test_all_success(self):
        ticket = OperationResult.success(data="T1")
        with patch("features.launcher.RobloxAPI.get_auth_ticket",
                   return_value=ticket), \
             patch("features.launcher.os.startfile"), \
             patch("features.launcher.settings_store.get",
                   return_value="default"), \
             patch("features.launcher.time.sleep"):
            result = launcher.launch_home_batch(
                [("a", {"cookie": "1"}), ("b", {"cookie": "2"})],
            )
        self.assertTrue(result)

    def test_partial_failure_returns_partial(self):
        ticket_ok = OperationResult.success(data="T1")
        ticket_bad = OperationResult.failure("COOKIE_INVALID", "Bad", "Rejected.")
        with patch("features.launcher.RobloxAPI.get_auth_ticket",
                   side_effect=[ticket_ok, ticket_bad]), \
             patch("features.launcher.os.startfile"), \
             patch("features.launcher.settings_store.get",
                   return_value="default"), \
             patch("features.launcher.time.sleep"):
            result = launcher.launch_home_batch(
                [("a", {"cookie": "1"}), ("b", {"cookie": "2"})],
            )
        self.assertFalse(result)
        self.assertEqual(result.code, "PARTIAL_LAUNCH")


if __name__ == "__main__":
    unittest.main()