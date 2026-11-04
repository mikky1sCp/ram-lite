from __future__ import annotations
import copy
import json
import os
import threading
import time

from utils.app_paths import get_data_dir
from utils.atomic_io import write_json_atomic

_SETTINGS_PATH = os.path.join(get_data_dir(), "settings.json")
_LOCK = threading.RLock()
_CACHE: dict = {}
_LOADED = False
_MTIME_NS: int | None = None
_LAST_STAT = 0.0
_STAT_INTERVAL = 0.5


def _get_mtime_ns() -> int | None:
    try:
        return os.stat(_SETTINGS_PATH).st_mtime_ns
    except OSError:
        return None


def _load_locked() -> None:
    global _CACHE, _LOADED, _MTIME_NS, _LAST_STAT
    data: dict = {}
    try:
        with open(_SETTINGS_PATH, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        if isinstance(loaded, dict):
            data = loaded
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        pass
    _CACHE = data
    _MTIME_NS = _get_mtime_ns()
    _LAST_STAT = time.monotonic()
    _LOADED = True


def _refresh_locked() -> None:
    global _LAST_STAT
    now = time.monotonic()
    if _LOADED and now - _LAST_STAT < _STAT_INTERVAL:
        return
    _LAST_STAT = now
    if not _LOADED or _get_mtime_ns() != _MTIME_NS:
        _load_locked()


def _write_locked(settings: dict) -> None:
    global _CACHE, _LOADED, _MTIME_NS, _LAST_STAT
    write_json_atomic(_SETTINGS_PATH, settings, prefix=".settings.", fsync=True)
    _CACHE = copy.deepcopy(settings)
    _MTIME_NS = _get_mtime_ns()
    _LAST_STAT = time.monotonic()
    _LOADED = True


def load() -> dict:
    with _LOCK:
        _refresh_locked()
        return copy.deepcopy(_CACHE)


def get(key: str, default=None):
    with _LOCK:
        _refresh_locked()
        return copy.deepcopy(_CACHE.get(key, default))


def save(key: str, value) -> bool:
    with _LOCK:
        _refresh_locked()
        if _CACHE.get(key) == value:
            return False
        updated = copy.deepcopy(_CACHE)
        updated[key] = copy.deepcopy(value)
        _write_locked(updated)
        return True


def invalidate() -> None:
    global _LOADED, _LAST_STAT
    with _LOCK:
        _LOADED = False
        _LAST_STAT = 0.0