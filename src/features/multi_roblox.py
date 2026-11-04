from __future__ import annotations

import ctypes
import threading
from ctypes import wintypes

import psutil

from classes.operation_result import OperationResult

_MUTEX_NAMES = (
    "ROBLOX_singletonEvent",
    "ROBLOX_SingletonEvent",
    "ROBLOX_singletonMutex",
)
_ERROR_ALREADY_EXISTS = 183

_LOCK = threading.RLock()
_handles: list[dict] = []


def _kernel32():
    k = ctypes.WinDLL("kernel32", use_last_error=True)
    k.CreateMutexW.restype = wintypes.HANDLE
    k.CreateMutexW.argtypes = [
        wintypes.LPCVOID, wintypes.BOOL, wintypes.LPCWSTR,
    ]
    k.CloseHandle.restype = wintypes.BOOL
    k.CloseHandle.argtypes = [wintypes.HANDLE]
    return k


def is_roblox_running() -> bool:
    for proc in psutil.process_iter(["name"]):
        name = (proc.info.get("name") or "").lower()
        if name == "robloxplayerbeta.exe":
            return True
    return False


def is_enabled() -> bool:
    with _LOCK:
        return bool(_handles)


def enable() -> OperationResult:
    with _LOCK:
        if _handles:
            return OperationResult.success("Multi Roblox is already enabled.")
        if is_roblox_running():
            return OperationResult.failure(
                "ROBLOX_RUNNING",
                "Roblox Is Already Running",
                "Close all Roblox clients before enabling Multi Roblox.",
            )
        kernel32 = _kernel32()
        created: list[dict] = []
        for name in _MUTEX_NAMES:
            try:
                ctypes.set_last_error(0)
                handle = kernel32.CreateMutexW(None, True, name)
                last_error = ctypes.get_last_error()
            except OSError as exc:
                continue
            if not handle:
                continue
            created.append({
                "name": name,
                "handle": handle,
                "owned": last_error != _ERROR_ALREADY_EXISTS,
            })
        if not created:
            return OperationResult.failure(
                "MUTEX_FAILED",
                "Multi Roblox Failed",
                "Windows did not allow the singleton mutex to be created.",
            )
        _handles.extend(created)
        return OperationResult.success(
            "Multi Roblox enabled. Launch Roblox as usual.",
        )


def disable() -> None:
    with _LOCK:
        kernel32 = _kernel32()
        for entry in _handles:
            handle = entry.get("handle")
            if not handle:
                continue
            try:
                kernel32.CloseHandle(handle)
            except OSError:
                pass
        _handles.clear()