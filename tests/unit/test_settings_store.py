from __future__ import annotations
import os
import tempfile
import unittest
from unittest.mock import patch

from features import settings_store


class SettingsStoreTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = os.path.join(self.folder.name, "settings.json")
        self.enterContext(
            patch.object(settings_store, "_SETTINGS_PATH", self.path)
        )
        settings_store.invalidate()
        self.addCleanup(settings_store.invalidate)

    def test_missing_key_returns_default(self):
        self.assertIsNone(settings_store.get("missing"))
        self.assertEqual(settings_store.get("missing", "x"), "x")

    def test_save_and_get_roundtrip(self):
        self.assertTrue(settings_store.save("theme", "dark"))
        self.assertEqual(settings_store.get("theme"), "dark")
        settings_store.invalidate()
        self.assertEqual(settings_store.get("theme"), "dark")

    def test_saving_same_value_returns_false(self):
        settings_store.save("theme", "dark")
        self.assertFalse(settings_store.save("theme", "dark"))

    def test_load_returns_copy(self):
        settings_store.save("nested", {"a": 1})
        data = settings_store.load()
        data["nested"]["a"] = 999
        self.assertEqual(settings_store.get("nested"), {"a": 1})


if __name__ == "__main__":
    unittest.main()