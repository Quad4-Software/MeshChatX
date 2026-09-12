# SPDX-License-Identifier: 0BSD

"""Shared backend constants.

Wire-contract values (HTTP API prefix, WebSocket inbound message types)
and timing defaults used by more than one manager live here so each is
defined exactly once. Domain-local constants stay in their manager
module.
"""

from __future__ import annotations

# pyright: strict
from enum import StrEnum

API_V1_PREFIX = "/api/v1"


class WsInboundType(StrEnum):
    """Client-to-server WebSocket message types.

    Members compare and hash equal to their string values, so handler
    registries keyed on them still resolve raw client-supplied strings.
    """

    PING = "ping"
    CONFIG_SET = "config.set"
    KEYBOARD_SHORTCUTS_GET = "keyboard_shortcuts.get"
    KEYBOARD_SHORTCUTS_SET = "keyboard_shortcuts.set"
    KEYBOARD_SHORTCUTS_DELETE = "keyboard_shortcuts.delete"
    LXM_GENERATE_PAPER_URI = "lxm.generate_paper_uri"
    LXM_INGEST_URI = "lxm.ingest_uri"
    LXMF_FORWARDING_RULE_ADD = "lxmf.forwarding.rule.add"
    LXMF_FORWARDING_RULE_DELETE = "lxmf.forwarding.rule.delete"
    LXMF_FORWARDING_RULE_TOGGLE = "lxmf.forwarding.rule.toggle"
    LXMF_FORWARDING_RULES_GET = "lxmf.forwarding.rules.get"
    NOMADNET_DOWNLOAD_CANCEL = "nomadnet.download.cancel"
    NOMADNET_FILE_DOWNLOAD = "nomadnet.file.download"
    NOMADNET_PAGE_ARCHIVE_ADD = "nomadnet.page.archive.add"
    NOMADNET_PAGE_ARCHIVE_FLUSH = "nomadnet.page.archive.flush"
    NOMADNET_PAGE_ARCHIVE_LOAD = "nomadnet.page.archive.load"
    NOMADNET_PAGE_ARCHIVES_GET = "nomadnet.page.archives.get"
    NOMADNET_PAGE_DOWNLOAD = "nomadnet.page.download"
    RNS_LINK_CLOSE = "rns.link.close"
    RNS_LINK_IDENTIFY = "rns.link.identify"
    RNS_LINK_OPEN = "rns.link.open"
    RNS_LINK_REQUEST = "rns.link.request"
    RNS_LINK_SEND = "rns.link.send"
    SYNC_SUBSCRIBE = "sync.subscribe"
    WS_CAPS = "ws.caps"
    WS_SUBSCRIBE = "ws.subscribe"
    WS_UNSUBSCRIBE = "ws.unsubscribe"


# Handled by the WS dispatcher itself before the handler registry lookup.
WS_RUNTIME_CONTROL_TYPES = frozenset(
    {
        WsInboundType.WS_SUBSCRIBE,
        WsInboundType.WS_UNSUBSCRIBE,
        WsInboundType.SYNC_SUBSCRIBE,
        WsInboundType.WS_CAPS,
    },
)

# Types allowed without an authenticated session. Everything else fails
# closed through websocket_type_requires_auth.
WS_PUBLIC_TYPES = frozenset({WsInboundType.PING, *WS_RUNTIME_CONTROL_TYPES})

# Shared announce cadence bounds for managers that republish on a timer.
MIN_ANNOUNCE_INTERVAL_SECONDS = 60
DEFAULT_ANNOUNCE_INTERVAL_SECONDS = 900
MAX_ANNOUNCE_INTERVAL_SECONDS = 86400
