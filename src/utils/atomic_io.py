from __future__ import annotations
import json
import os
import tempfile


def write_json_atomic(
    path: str, data, *, prefix: str = ".atomic.", fsync: bool = False
) -> None:
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=prefix, suffix=".tmp", dir=directory)
    try:
        try:
            handle = os.fdopen(fd, "w", encoding="utf-8")
        except BaseException:
            os.close(fd)
            raise
        with handle:
            json.dump(data, handle, indent=2, ensure_ascii=False)
            if fsync:
                handle.flush()
                os.fsync(handle.fileno())
        os.replace(tmp_path, path)
    except BaseException:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        raise