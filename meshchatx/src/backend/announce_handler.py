# SPDX-License-Identifier: 0BSD

"""RNS announce callback adapter that retains the aspect filter string."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

_log = logging.getLogger("meshchatx.announce")


class AnnounceHandler:
    """Forwards RNS announce callbacks while injecting the aspect filter.

    RNS does not include the registered aspect on the announce callback, so
    callers register one handler instance per aspect and get the filter back
    on every receive.
    """

    __slots__ = ("aspect_filter", "received_announce_callback")

    def __init__(
        self,
        aspect_filter: str,
        received_announce_callback: Callable[..., Any],
    ) -> None:
        self.aspect_filter = aspect_filter
        self.received_announce_callback = received_announce_callback

    def received_announce(
        self,
        destination_hash: Any,
        announced_identity: Any,
        app_data: Any,
        announce_packet_hash: Any,
    ) -> None:
        try:
            self.received_announce_callback(
                self.aspect_filter,
                destination_hash,
                announced_identity,
                app_data,
                announce_packet_hash,
            )
        except Exception as exc:
            _log.debug("Failed to handle received announce: %s", exc)
