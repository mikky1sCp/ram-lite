from __future__ import annotations
import unittest
from unittest.mock import MagicMock, patch

import requests

from features import avatars


def _response(status: int, json_data=None, content: bytes = b"") -> MagicMock:
    r = MagicMock()
    r.status_code = status
    if json_data is not None:
        r.json.return_value = json_data
    r.content = content
    return r


class FetchAvatarUrlTests(unittest.TestCase):
    def test_returns_url_from_valid_response(self):
        payload = {"data": [{"imageUrl": "https://cdn.example/a.png"}]}
        with patch("features.avatars.requests.get", return_value=_response(200, payload)):
            self.assertEqual(
                avatars.fetch_avatar_url("123"),
                "https://cdn.example/a.png",
            )

    def test_empty_data_returns_none(self):
        with patch("features.avatars.requests.get", return_value=_response(200, {"data": []})):
            self.assertIsNone(avatars.fetch_avatar_url("123"))

    def test_http_error_returns_none(self):
        with patch("features.avatars.requests.get", return_value=_response(500)):
            self.assertIsNone(avatars.fetch_avatar_url("123"))

    def test_network_error_returns_none(self):
        with patch("features.avatars.requests.get",
                   side_effect=requests.ConnectionError()):
            self.assertIsNone(avatars.fetch_avatar_url("123"))


class DownloadAvatarTests(unittest.TestCase):
    def setUp(self):
        with avatars._CACHE_LOCK:
            avatars._MEMORY_CACHE.clear()

    def test_downloads_and_caches(self):
        url_resp = _response(200, {"data": [{"imageUrl": "https://cdn.example/a.png"}]})
        png_resp = _response(200, content=b"\x89PNG...")
        with patch("features.avatars.requests.get", side_effect=[url_resp, png_resp]):
            self.assertEqual(avatars.download_avatar("123"), b"\x89PNG...")
        # Second call must hit the cache (no HTTP).
        with patch("features.avatars.requests.get") as mock_get:
            self.assertEqual(avatars.download_avatar("123"), b"\x89PNG...")
        mock_get.assert_not_called()

    def test_empty_user_id_returns_none(self):
        self.assertIsNone(avatars.download_avatar(""))
        self.assertIsNone(avatars.download_avatar("0"))

    def test_missing_url_returns_none(self):
        with patch("features.avatars.requests.get",
                   return_value=_response(200, {"data": []})):
            self.assertIsNone(avatars.download_avatar("123"))

    def test_failed_download_returns_none(self):
        url_resp = _response(200, {"data": [{"imageUrl": "https://cdn.example/a.png"}]})
        png_resp = _response(500)
        with patch("features.avatars.requests.get", side_effect=[url_resp, png_resp]):
            self.assertIsNone(avatars.download_avatar("123"))


if __name__ == "__main__":
    unittest.main()