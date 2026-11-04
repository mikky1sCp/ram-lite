from __future__ import annotations
import os
import sys


def get_project_root() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    source_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if os.path.basename(source_root).casefold() == "src":
        return os.path.dirname(source_root)
    return source_root


def get_data_dir() -> str:
    override = os.environ.get("RAM_DATA_DIR", "").strip()
    if override:
        return os.path.abspath(os.path.expanduser(override))
    return os.path.join(get_project_root(), "AccountManagerData")