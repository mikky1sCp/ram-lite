from __future__ import annotations
import json
import os
import tempfile
import unittest

from utils.atomic_io import write_json_atomic


class AtomicIoTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)

    def _path(self) -> str:
        return os.path.join(self.folder.name, "data.json")

    def test_roundtrip(self):
        write_json_atomic(self._path(), {"a": 1})
        with open(self._path(), encoding="utf-8") as f:
            self.assertEqual(json.load(f), {"a": 1})

    def test_overwrite(self):
        write_json_atomic(self._path(), {"a": 1})
        write_json_atomic(self._path(), {"a": 2})
        with open(self._path(), encoding="utf-8") as f:
            self.assertEqual(json.load(f), {"a": 2})

    def test_creates_parent_directory(self):
        nested = os.path.join(self.folder.name, "a", "b", "data.json")
        write_json_atomic(nested, {"ok": True})
        self.assertTrue(os.path.isfile(nested))


if __name__ == "__main__":
    unittest.main()