from __future__ import annotations

import collections
import threading

import requests

_AVATAR_URL = "https://thumbnails.roblox.com/v1/users/avatar-headshot"
_THUMBNAIL_TIMEOUT = 8
_DOWNLOAD_TIMEOUT = 10

_MEMORY_CACHE: collections.OrderedDict[str, bytes] = collections.OrderedDict()
_CACHE_LIMIT = 256
_CACHE_LOCK = threading.RLock()


def _remember(user_id: str, data: bytes) -> None:
    with _CACHE_LOCK:
        _MEMORY_CACHE[user_id] = data
        _MEMORY_CACHE.move_to_end(user_id)
        while len(_MEMORY_CACHE) > _CACHE_LIMIT:
            _MEMORY_CACHE.popitem(last=False)


def get_cached(user_id: str) -> bytes | None:
    with _CACHE_LOCK:
        return _MEMORY_CACHE.get(str(user_id))


def fetch_avatar_url(user_id: str) -> str | None:
    try:
        response = requests.get(
            _AVATAR_URL,
            params={
                "userIds": str(user_id),
                "size": "100x100",
                "format": "Png",
                "isCircular": "true",
            },
            timeout=_THUMBNAIL_TIMEOUT,
        )
    except requests.RequestException:
        return None
    if response.status_code != 200:
        return None
    try:
        entries = response.json().get("data", [])
    except ValueError:
        return None
    if not entries:
        return None
    url = entries[0].get("imageUrl")
    return str(url) if url else None


def download_avatar(user_id: str) -> bytes | None:
    """Fetch the PNG bytes for a user's avatar, using the in-memory cache."""
    uid = str(user_id)
    if not uid or uid == "0":
        return None
    cached = get_cached(uid)
    if cached is not None:
        return cached

    url = fetch_avatar_url(uid)
    if not url:
        return None
    try:
        response = requests.get(url, timeout=_DOWNLOAD_TIMEOUT)
    except requests.RequestException:
        return None
    if response.status_code != 200 or not response.content:
        return None
    _remember(uid, response.content)
    return response.content