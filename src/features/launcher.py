from __future__ import annotations

import os
import secrets
import time

from classes.operation_result import OperationResult
from classes.roblox_api import RobloxAPI
from features import settings_store


def _browser_tracker_id() -> int:
    return secrets.randbelow(8_000_000_000_000_000) + 1_000_000_000_000_000


def build_home_url(ticket: str) -> str:
    tracker = _browser_tracker_id()
    launch_time = int(time.time() * 1000)
    return (
        "roblox-player:1+launchmode:play"
        f"+gameinfo:{ticket}"
        f"+launchtime:{launch_time}"
        f"+browsertrackerid:{tracker}"
        "+robloxLocale:en_us+gameLocale:en_us"
    )


def build_place_url(ticket: str, place_id: str) -> str:
    tracker = _browser_tracker_id()
    launch_time = int(time.time() * 1000)
    return (
        "roblox-player:1+launchmode:play"
        f"+gameinfo:{ticket}"
        f"+launchtime:{launch_time}"
        "+placelauncherurl:https://assetgame.roblox.com/game/PlaceLauncher.ashx"
        "?request=RequestGame"
        f"&browserTrackerId={tracker}"
        f"&placeId={place_id}"
        "&isPlayTogetherGame=false"
        f"+browsertrackerid:{tracker}"
        "+robloxLocale:en_us+gameLocale:en_us"
    )


def _launch_url(url: str) -> OperationResult:
    launcher = settings_store.get("roblox_launcher", "default")
    if launcher != "default":
        return OperationResult.failure(
            "LAUNCHER_UNSUPPORTED", "Launcher Not Supported Yet",
            "Only the default Windows handler is available in this build.",
            detail=f"Configured launcher: {launcher}",
        )
    try:
        os.startfile(url)
    except OSError as exc:
        return OperationResult.failure(
            "LAUNCH_FAILED", "Roblox Could Not Start",
            "Windows could not open the roblox-player link. "
            "Install Roblox from roblox.com and try again.",
            detail=str(exc),
        )
    return OperationResult.success("Roblox launch requested.")


def launch_home(account_data: dict) -> OperationResult:
    cookie = account_data.get("cookie", "")
    ticket = RobloxAPI.get_auth_ticket(cookie)
    if not ticket:
        return ticket
    return _launch_url(build_home_url(ticket.data))


def launch_place(account_data: dict, place_id: str) -> OperationResult:
    pid = str(place_id or "").strip()
    if not pid.isdigit():
        return OperationResult.failure(
            "PLACE_ID_INVALID", "Invalid Place ID",
            "The Place ID must contain only digits.",
        )
    cookie = account_data.get("cookie", "")
    ticket = RobloxAPI.get_auth_ticket(cookie)
    if not ticket:
        return ticket
    return _launch_url(build_place_url(ticket.data, pid))