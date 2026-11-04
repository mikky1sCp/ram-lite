from __future__ import annotations

import requests

from classes.operation_result import OperationResult

_AUTH_URL = "https://users.roblox.com/v1/users/authenticated"
_TIMEOUT = 8


class RobloxAPI:
    """Thin wrapper around the Roblox endpoints we actually need."""

    @staticmethod
    def get_user_info_from_api(cookie: str) -> tuple[str, int] | None:
        """Return (username, user_id) or None if the cookie is rejected."""
        try:
            response = requests.get(
                _AUTH_URL,
                headers={"Cookie": f".ROBLOSECURITY={cookie}"},
                timeout=_TIMEOUT,
            )
        except requests.RequestException:
            return None
        if response.status_code != 200:
            return None
        try:
            data = response.json()
        except ValueError:
            return None
        username = data.get("name")
        user_id = data.get("id")
        if not username or not isinstance(user_id, int):
            return None
        return username, user_id

    @staticmethod
    def validate_cookie(cookie: str) -> OperationResult:
        """Detailed validation result for an existing cookie."""
        if not str(cookie or "").strip():
            return OperationResult.failure(
                "COOKIE_MISSING", "Cookie Missing",
                "Paste a Roblox security cookie.",
            )
        try:
            response = requests.get(
                _AUTH_URL,
                headers={"Cookie": f".ROBLOSECURITY={cookie}"},
                timeout=_TIMEOUT,
            )
        except requests.Timeout:
            return OperationResult.failure(
                "NETWORK_TIMEOUT", "Roblox Timed Out",
                "Roblox did not respond in time. Try again.",
            )
        except requests.RequestException as exc:
            return OperationResult.failure(
                "NETWORK_ERROR", "Could Not Reach Roblox",
                "Check your internet connection and try again.",
                detail=str(exc),
            )
        if response.status_code == 200:
            return OperationResult.success()
        if response.status_code in (401, 403):
            return OperationResult.failure(
                "COOKIE_INVALID", "Cookie Rejected",
                "Roblox rejected this cookie. Copy a fresh one.",
            )
        return OperationResult.failure(
            "VALIDATION_FAILED", "Cookie Could Not Be Verified",
            f"Roblox returned HTTP {response.status_code}.",
        )