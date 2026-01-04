import unittest
from unittest.mock import MagicMock
from meshchatx.src.backend.nomadnet_downloader import NomadnetDownloader


class TestNomadnetDownloader(unittest.TestCase):
    def setUp(self):
        self.dest_hash = b"123"
        self.path = "/test"
        self.on_success = MagicMock()
        self.on_failure = MagicMock()
        self.on_progress = MagicMock()
        self.downloader = NomadnetDownloader(
            self.dest_hash,
            self.path,
            None,
            self.on_success,
            self.on_failure,
            self.on_progress,
        )

    def test_cancel(self):
        self.downloader.request_receipt = MagicMock()
        self.downloader.cancel()
        self.assertTrue(self.downloader.is_cancelled)
        self.downloader.request_receipt.cancel.assert_called_once()


if __name__ == "__main__":
    unittest.main()
