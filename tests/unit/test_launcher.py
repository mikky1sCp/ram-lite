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
                   return_value="bloxstrap"), \
             patch("features.launcher.os.startfile") as start:
            result = launcher.launch_home({"cookie": "x"})
        self.assertFalse(result)
        self.assertEqual(result.code, "LAUNCHER_UNSUPPORTED")
        start.assert_not_called()


if __name__ == "__main__":
    unittest.main()