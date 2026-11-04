from __future__ import annotations
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
for folder in (PROJECT_ROOT, PROJECT_ROOT / "src"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))


def main() -> int:
    loader = unittest.TestLoader()
    suite = loader.discover(
        str(PROJECT_ROOT / "tests"),
        pattern="test_*.py",
        top_level_dir=str(PROJECT_ROOT),
    )
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())