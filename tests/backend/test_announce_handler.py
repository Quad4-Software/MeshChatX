# SPDX-License-Identifier: 0BSD

import unittest
from unittest.mock import MagicMock

from meshchatx.src.backend.announce_handler import AnnounceHandler


class TestAnnounceHandler(unittest.TestCase):
    def test_forwards_to_callback_with_aspect_filter(self):
        cb = MagicMock()
        handler = AnnounceHandler("test.aspect", cb)
        handler.received_announce(b"d", b"id", b"app", b"hash")
        cb.assert_called_once_with("test.aspect", b"d", b"id", b"app", b"hash")

    def test_swallows_callback_exception(self):
        def bad_cb(_aspect, *_args):
            raise RuntimeError("simulated handler failure")

        handler = AnnounceHandler("a", bad_cb)
        handler.received_announce(b"d", b"id", b"app", b"h")
