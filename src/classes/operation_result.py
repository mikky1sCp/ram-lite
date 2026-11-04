from __future__ import annotations
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class OperationResult:
    ok: bool
    code: str = ""
    title: str = ""
    message: str = ""
    detail: str = ""
    data: Any = None

    def __bool__(self) -> bool:
        return self.ok

    @classmethod
    def success(cls, message: str = "", data=None):
        return cls(True, message=message, data=data)

    @classmethod
    def failure(cls, code: str, title: str, message: str, detail: str = ""):
        return cls(False, code=code, title=title, message=message, detail=detail)