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

class GetAuthTicketTests(unittest.TestCase):
    def _response(self, status, ticket=None, csrf=None):
        r = MagicMock()
        r.status_code = status
        r.headers = {}
        if ticket:
            r.headers["rbx-authentication-ticket"] = ticket
        if csrf:
            r.headers["x-csrf-token"] = csrf
        return r

    def test_direct_success(self):
        with patch("classes.roblox_api.requests.post",
                   return_value=self._response(200, ticket="T1")):
            result = RobloxAPI.get_auth_ticket("cookie")
            self.assertTrue(result)
            self.assertEqual(result.data, "T1")

    def test_csrf_then_success(self):
        responses = [
            self._response(403, csrf="csrf-token"),
            self._response(200, ticket="T2"),
        ]
        with patch("classes.roblox_api.requests.post", side_effect=responses):
            result = RobloxAPI.get_auth_ticket("cookie")
            self.assertTrue(result)
            self.assertEqual(result.data, "T2")

    def test_401_without_csrf_returns_invalid(self):
        with patch("classes.roblox_api.requests.post",
                   return_value=self._response(401)):
            result = RobloxAPI.get_auth_ticket("cookie")
            self.assertFalse(result)
            self.assertEqual(result.code, "COOKIE_INVALID")

    def test_429_returns_rate_limited(self):
        with patch("classes.roblox_api.requests.post",
                   return_value=self._response(429)):
            result = RobloxAPI.get_auth_ticket("cookie")
            self.assertFalse(result)
            self.assertEqual(result.code, "RATE_LIMITED")

    def test_timeout_returns_network_timeout(self):
        with patch("classes.roblox_api.requests.post",
                   side_effect=requests.Timeout()):
            result = RobloxAPI.get_auth_ticket("cookie")
            self.assertFalse(result)
            self.assertEqual(result.code, "NETWORK_TIMEOUT")

    def test_empty_cookie_returns_missing(self):
        result = RobloxAPI.get_auth_ticket("")
        self.assertFalse(result)
        self.assertEqual(result.code, "COOKIE_MISSING")

if __name__ == "__main__":
    unittest.main()