from __future__ import annotations
import unittest
from unittest.mock import MagicMock, patch

import requests

from classes.roblox_api import RobloxAPI


def _response(status: int, payload=None) -> MagicMock:
    r = MagicMock()
    r.status_code = status
    if payload is not None:
        r.json.return_value = payload
    return r


class GetUserInfoTests(unittest.TestCase):
    def test_valid_cookie_returns_username_and_id(self):
        with patch("classes.roblox_api.requests.get",
                   return_value=_response(200, {"name": "alice", "id": 123})):
            self.assertEqual(RobloxAPI.get_user_info_from_api("cookie"), ("alice", 123))

    def test_unauthorized_returns_none(self):
        with patch("classes.roblox_api.requests.get", return_value=_response(401)):
            self.assertIsNone(RobloxAPI.get_user_info_from_api("cookie"))

    def test_network_error_returns_none(self):
        with patch("classes.roblox_api.requests.get",
                   side_effect=requests.ConnectionError()):
            self.assertIsNone(RobloxAPI.get_user_info_from_api("cookie"))

    def test_missing_fields_returns_none(self):
        with patch("classes.roblox_api.requests.get",
                   return_value=_response(200, {"name": "alice"})):
            self.assertIsNone(RobloxAPI.get_user_info_from_api("cookie"))


class ValidateCookieTests(unittest.TestCase):
    def test_ok_returns_success(self):
        with patch("classes.roblox_api.requests.get", return_value=_response(200)):
            self.assertTrue(RobloxAPI.validate_cookie("cookie"))

    def test_401_returns_invalid(self):
        with patch("classes.roblox_api.requests.get", return_value=_response(401)):
            result = RobloxAPI.validate_cookie("cookie")
            self.assertFalse(result)
            self.assertEqual(result.code, "COOKIE_INVALID")

    def test_empty_cookie_returns_missing(self):
        result = RobloxAPI.validate_cookie("")
        self.assertFalse(result)
        self.assertEqual(result.code, "COOKIE_MISSING")

    def test_timeout_returns_network_error(self):
        with patch("classes.roblox_api.requests.get",
                   side_effect=requests.Timeout()):
            result = RobloxAPI.validate_cookie("cookie")
            self.assertEqual(result.code, "NETWORK_TIMEOUT")


if __name__ == "__main__":
    unittest.main()