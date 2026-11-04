from __future__ import annotations
import unittest
from unittest.mock import MagicMock, patch

from features import multi_roblox


class ToggleTests(unittest.TestCase):
    def setUp(self):
        multi_roblox.disable()

    def test_enable_without_roblox_creates_mutexes(self):
        fake_kernel = MagicMock()
        fake_kernel.CreateMutexW.return_value = 12345
        with patch("features.multi_roblox._kernel32", return_value=fake_kernel), \
             patch("features.multi_roblox.is_roblox_running", return_value=False), \
             patch("features.multi_roblox.ctypes.get_last_error", return_value=0):
            result = multi_roblox.enable()
        self.assertTrue(result)
        self.assertTrue(multi_roblox.is_enabled())

    def test_enable_refuses_when_roblox_running(self):
        with patch("features.multi_roblox.is_roblox_running", return_value=True):
            result = multi_roblox.enable()
        self.assertFalse(result)
        self.assertEqual(result.code, "ROBLOX_RUNNING")
        self.assertFalse(multi_roblox.is_enabled())

    def test_enable_twice_is_idempotent(self):
        fake_kernel = MagicMock()
        fake_kernel.CreateMutexW.return_value = 1
        with patch("features.multi_roblox._kernel32", return_value=fake_kernel), \
             patch("features.multi_roblox.is_roblox_running", return_value=False), \
             patch("features.multi_roblox.ctypes.get_last_error", return_value=0):
            first = multi_roblox.enable()
            second = multi_roblox.enable()
        self.assertTrue(first)
        self.assertTrue(second)

    def test_disable_releases_handles(self):
        fake_kernel = MagicMock()
        fake_kernel.CreateMutexW.return_value = 99
        with patch("features.multi_roblox._kernel32", return_value=fake_kernel), \
             patch("features.multi_roblox.is_roblox_running", return_value=False), \
             patch("features.multi_roblox.ctypes.get_last_error", return_value=0):
            multi_roblox.enable()
            multi_roblox.disable()
        self.assertFalse(multi_roblox.is_enabled())
        fake_kernel.CloseHandle.assert_called()


if __name__ == "__main__":
    unittest.main()