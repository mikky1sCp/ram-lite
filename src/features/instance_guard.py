from __future__ import annotations

import ctypes
import threading
import time
from ctypes import wintypes

import psutil

# --- Native Windows API Definitions ---
ntdll = ctypes.WinDLL("ntdll", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

SystemExtendedHandleInformation = 64
STATUS_INFO_LENGTH_MISMATCH = 0xC0000004
STATUS_SUCCESS = 0
DUPLICATE_CLOSE_SOURCE = 0x00000001
PROCESS_DUP_HANDLE = 0x0040

class SYSTEM_HANDLE_TABLE_ENTRY_INFO_EX(ctypes.Structure):
    _fields_ = [
        ("Object", ctypes.c_void_p),
        ("UniqueProcessId", ctypes.c_size_t),
        ("HandleValue", ctypes.c_size_t),
        ("GrantedAccess", ctypes.c_ulong),
        ("CreatorBackTraceIndex", ctypes.c_ushort),
        ("ObjectTypeIndex", ctypes.c_ushort),
        ("HandleAttributes", ctypes.c_ulong),
        ("Reserved", ctypes.c_ulong),
    ]

class SYSTEM_HANDLE_INFORMATION_EX(ctypes.Structure):
    _fields_ = [
        ("NumberOfHandles", ctypes.c_size_t),
        ("Reserved", ctypes.c_size_t),
        ("Handles", SYSTEM_HANDLE_TABLE_ENTRY_INFO_EX * 1),
    ]

# Set up function signatures
ntdll.NtQuerySystemInformation.argtypes = [
    ctypes.c_int, ctypes.c_void_p, ctypes.c_ulong, ctypes.POINTER(ctypes.c_ulong)
]
ntdll.NtQuerySystemInformation.restype = ctypes.c_long
ntdll.NtQueryObject.argtypes = [
    wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, ctypes.c_ulong, ctypes.POINTER(ctypes.c_ulong)
]
ntdll.NtQueryObject.restype = ctypes.c_long

kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL
kernel32.GetCurrentProcess.restype = wintypes.HANDLE

TARGET_HANDLE_NAME = "ROBLOX_singletonEvent"


def _get_all_handles() -> list[SYSTEM_HANDLE_TABLE_ENTRY_INFO_EX]:
    """Get a snapshot of all handles in the system."""
    length = 0
    status = ntdll.NtQuerySystemInformation(
        SystemExtendedHandleInformation, None, 0, ctypes.byref(ctypes.c_ulong(length))
    )
    if status != STATUS_INFO_LENGTH_MISMATCH:
        return []
    buffer = ctypes.create_string_buffer(length.value)
    status = ntdll.NtQuerySystemInformation(
        SystemExtendedHandleInformation,
        buffer,
        length.value,
        ctypes.byref(ctypes.c_ulong(length)),
    )
    if status != STATUS_SUCCESS:
        return []
    info = ctypes.cast(buffer, ctypes.POINTER(SYSTEM_HANDLE_INFORMATION_EX)).contents
    return list(info.Handles)[:info.NumberOfHandles]


def _get_handle_name(process_handle: wintypes.HANDLE, handle_value: int) -> str | None:
    """Resolve a handle to its object name."""
    # Query object name information
    # This requires a buffer that may be resized based on the returned length.
    length = 0
    # First, query the required buffer size.
    ntdll.NtQueryObject(handle_value, 1, None, 0, ctypes.byref(ctypes.c_ulong(length)))
    if length.value == 0:
        return None
    buffer = ctypes.create_string_buffer(length.value)
    status = ntdll.NtQueryObject(
        handle_value, 1, buffer, length.value, ctypes.byref(ctypes.c_ulong(length))
    )
    if status != STATUS_SUCCESS:
        return None
    # The structure is UNICODE_STRING followed by the actual string buffer.
    # UNICODE_STRING: USHORT Length, USHORT MaximumLength, PWSTR Buffer
    # We can read the Length and then decode the string.
    # This is a simplified parsing; a robust implementation would use a proper struct.
    try:
        # The first 2 bytes are Length (in bytes), next 2 are MaximumLength.
        length_bytes = int.from_bytes(buffer.raw[:2], "little")
        if length_bytes == 0:
            return None
        name = buffer.raw[4:4 + length_bytes].decode("utf-16-le", errors="ignore")
        return name
    except Exception:
        return None


def _close_handle_in_process(pid: int, handle_value: int) -> bool:
    """Close a specific handle in a target process."""
    process = kernel32.OpenProcess(PROCESS_DUP_HANDLE, False, pid)
    if not process:
        return False
    dup = wintypes.HANDLE()
    try:
        # Duplicate the handle into our process with DUPLICATE_CLOSE_SOURCE.
        # This closes the original handle in the target process.
        success = kernel32.DuplicateHandle(
            process, handle_value,
            kernel32.GetCurrentProcess(), ctypes.byref(dup),
            0, False, DUPLICATE_CLOSE_SOURCE,
        )
        if success:
            kernel32.CloseHandle(dup)  # Close our copy as well.
            return True
        return False
    finally:
        kernel32.CloseHandle(process)


class InstanceGuard:
    def __init__(self, interval: float = 3.0):
        self.interval = interval
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="InstanceGuard")
        self._thread.start()
        print("[InstanceGuard] Started.")

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None
        print("[InstanceGuard] Stopped.")

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self._sweep()
            except Exception as exc:
                print(f"[InstanceGuard] Sweep error: {exc}")
            self._stop.wait(self.interval)

    def _sweep(self) -> None:
        """Find Roblox processes and close their singleton handle."""
        target_pids = {
            p.pid for p in psutil.process_iter(["name"])
            if (p.info.get("name") or "").lower() == "robloxplayerbeta.exe"
        }
        if not target_pids:
            return

        all_handles = _get_all_handles()
        for entry in all_handles:
            if entry.UniqueProcessId not in target_pids:
                continue

            # Open the target process to query the handle name.
            process = kernel32.OpenProcess(PROCESS_DUP_HANDLE, False, entry.UniqueProcessId)
            if not process:
                continue

            dup = wintypes.HANDLE()
            try:
                # Duplicate the handle into our process to query its name.
                success = kernel32.DuplicateHandle(
                    process, entry.HandleValue,
                    kernel32.GetCurrentProcess(), ctypes.byref(dup),
                    0, False, 0x00000002,  # DUPLICATE_SAME_ACCESS
                )
                if not success:
                    continue
                # Query the name of the duplicated handle.
                name = _get_handle_name(kernel32.GetCurrentProcess(), dup)
                if name and TARGET_HANDLE_NAME in name:
                    print(f"[InstanceGuard] Found target handle {entry.HandleValue} in PID {entry.UniqueProcessId}")
                    if _close_handle_in_process(entry.UniqueProcessId, entry.HandleValue):
                        print(f"[InstanceGuard] Successfully closed handle in PID {entry.UniqueProcessId}")
            finally:
                if dup:
                    kernel32.CloseHandle(dup)
                kernel32.CloseHandle(process)