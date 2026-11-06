from __future__ import annotations

import threading
from typing import Callable

from classes.operation_result import OperationResult
from classes.roblox_api import RobloxAPI


def validate_all_cookies(
    manager,
    on_progress: Callable[[str, bool], None],
    on_done: Callable[[int, int], None],
    delay: float = 1.5,
    stop_event: threading.Event | None = None,
) -> None:
    """Validate every saved cookie sequentially.

    ``on_progress(username, is_valid)`` is called only for accounts whose
    status was decided. Network errors and rate limits are skipped: they
    leave the previous status untouched, because an unreachable server
    does not mean the cookie is dead.
    """
    stop = stop_event or threading.Event()
    valid_count = 0
    invalid_count = 0
    changed = False

    usernames = list(manager.accounts.keys())
    for index, username in enumerate(usernames):
        if stop.is_set():
            break
        data = manager.accounts.get(username)
        if not isinstance(data, dict):
            continue
        cookie = str(data.get("cookie", "") or "")
        if not cookie:
            continue

        result = RobloxAPI.validate_cookie(cookie)
        status: bool | None
        if result:
            status = True
        elif result.code == "COOKIE_INVALID":
            status = False
        else:
            status = None

        if status is not None:
            manager.set_cookie_status(username, status, save=False)
            changed = True
            if status:
                valid_count += 1
            else:
                invalid_count += 1
            try:
                on_progress(username, status)
            except Exception:
                pass

        if index < len(usernames) - 1 and stop.wait(max(0.0, delay)):
            break

    if changed:
        try:
            manager.save_accounts()
        except Exception:
            pass
    try:
        on_done(valid_count, invalid_count)
    except Exception:
        pass