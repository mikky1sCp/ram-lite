from __future__ import annotations

import os
import secrets
import subprocess
import time
from pathlib import Path

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


def _local_appdata() -> str:
    return os.getenv("LOCALAPPDATA", "")


def _launch_via_default(url: str) -> OperationResult:
    try:
        os.startfile(url)
    except OSError as exc:
        return OperationResult.failure(
            "LAUNCH_FAILED", "Roblox Could Not Start",
            "Windows could not open the roblox-player link.",
            detail=str(exc),
        )
    return OperationResult.success("Roblox launch requested.")


def _launch_via_bloxstrap(url: str) -> OperationResult:
    local = _local_appdata()
    if not local:
        return OperationResult.failure(
            "LOCALAPPDATA_MISSING", "Windows App Data Missing",
            "The LOCALAPPDATA directory was not found.",
        )
    path = Path(local) / "Bloxstrap" / "Bloxstrap.exe"
    if not path.is_file():
        return OperationResult.failure(
            "BLOXSTRAP_NOT_INSTALLED", "Bloxstrap Not Found",
            "Install Bloxstrap or choose another launcher.",
            detail=f"Expected: {path}",
        )
    try:
        subprocess.Popen(
            [str(path), "-player", url],
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except OSError as exc:
        return OperationResult.failure(
            "LAUNCH_FAILED", "Bloxstrap Could Not Start", str(exc),
        )
    return OperationResult.success("Roblox launch requested via Bloxstrap.")


def _launch_via_client(url: str) -> OperationResult:
    local = _local_appdata()
    if not local:
        return OperationResult.failure(
            "LOCALAPPDATA_MISSING", "Windows App Data Missing",
            "The LOCALAPPDATA directory was not found.",
        )
    versions = Path(local) / "Roblox" / "Versions"
    if not versions.is_dir():
        return OperationResult.failure(
            "ROBLOX_NOT_INSTALLED", "Roblox Not Installed",
            "Install Roblox Player from roblox.com and try again.",
        )
    folders = sorted(
        (d for d in versions.iterdir()
         if d.is_dir() and d.name.startswith("version-")),
        key=lambda d: d.stat().st_mtime, reverse=True,
    )
    for folder in folders:
        exe = folder / "RobloxPlayerBeta.exe"
        if exe.is_file():
            try:
                subprocess.Popen(
                    [str(exe), url],
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
            except OSError as exc:
                return OperationResult.failure(
                    "LAUNCH_FAILED", "Roblox Client Could Not Start", str(exc),
                )
            return OperationResult.success("Roblox launch requested.")
    return OperationResult.failure(
        "ROBLOX_EXECUTABLE_MISSING", "Roblox Client Missing",
        "RobloxPlayerBeta.exe was not found in any installed version.",
    )


def _launch_url(url: str) -> OperationResult:
    launcher = settings_store.get("roblox_launcher", "default")
    if launcher == "bloxstrap":
        return _launch_via_bloxstrap(url)
    if launcher == "client":
        return _launch_via_client(url)
    if launcher == "default":
        return _launch_via_default(url)
    return OperationResult.failure(
        "LAUNCHER_UNSUPPORTED", "Unsupported Launcher",
        "The selected launcher is not supported.",
        detail=f"Configured launcher: {launcher}",
    )


def launch_home(account_data: dict) -> OperationResult:
    ticket = RobloxAPI.get_auth_ticket(account_data.get("cookie", ""))
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
    ticket = RobloxAPI.get_auth_ticket(account_data.get("cookie", ""))
    if not ticket:
        return ticket
    return _launch_url(build_place_url(ticket.data, pid))


def launch_home_batch(
    accounts: list[tuple[str, dict]],
    delay: float = 1.5,
) -> OperationResult:
    successes = 0
    failures: list[tuple[str, OperationResult]] = []
    for index, (username, data) in enumerate(accounts):
        if index > 0:
            time.sleep(delay)
        try:
            result = launch_home(data)
        except Exception as exc:
            result = OperationResult.failure(
                "LAUNCH_FAILED", "Launch Failed", str(exc),
            )
        if result:
            successes += 1
        else:
            failures.append((username, result))
    if not failures:
        return OperationResult.success(
            f"Launched {successes}/{len(accounts)} account(s)."
        )
    if successes == 0:
        first = failures[0][1]
        return OperationResult.failure(
            first.code or "LAUNCH_FAILED",
            first.title or "Launch Failed",
            first.message or "No accounts could be launched.",
            detail="\n".join(
                f"{u}: {r.code or 'ERROR'}" for u, r in failures
            ),
        )
    return OperationResult.failure(
        "PARTIAL_LAUNCH", "Partial Launch",
        f"Launched {successes}/{len(accounts)} account(s).",
        detail="\n".join(
            f"{u}: {r.message}" for u, r in failures
        ),
    )