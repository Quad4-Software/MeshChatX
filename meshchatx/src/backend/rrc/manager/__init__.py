# SPDX-License-Identifier: 0BSD

"""Re-export RRC client manager API."""

from __future__ import annotations

from meshchatx.src.backend.rrc.manager.actions import RRCHubActionsMixin
from meshchatx.src.backend.rrc.manager.connection import RRCHubConnectionMixin
from meshchatx.src.backend.rrc.manager.constants import (
    BAD_KEY_MARKERS,
    DEFAULT_DEST_NAME,
    FORCED_LEAVE_MARKERS,
    H_KIND,
    H_MENTION,
    H_NICK,
    H_SRC,
    H_TEXT,
    H_TS,
    HISTORY_DIR_NAME,
    HISTORY_FILENAME_SANITIZE_RE,
    SLOW_CHANNEL_BPS,
    _slow_connect_gate,
)
from meshchatx.src.backend.rrc.manager.core import *  # noqa: F403
from meshchatx.src.backend.rrc.manager.handlers import RRCHubPacketHandlersMixin
from meshchatx.src.backend.rrc.manager.history import RRCHubHistoryMixin
from meshchatx.src.backend.rrc.manager.hub import RRCHub
from meshchatx.src.backend.rrc.manager.manager import RRCManager
from meshchatx.src.backend.rrc.manager.persistence import RRCManagerPersistenceMixin
from meshchatx.src.backend.rrc.manager.room_keys import RRCManagerRoomKeysMixin

__all__ = [
    "BAD_KEY_MARKERS",
    "DEFAULT_DEST_NAME",
    "FORCED_LEAVE_MARKERS",
    "HISTORY_DIR_NAME",
    "HISTORY_FILENAME_SANITIZE_RE",
    "H_KIND",
    "H_MENTION",
    "H_NICK",
    "H_SRC",
    "H_TEXT",
    "H_TS",
    "RRCHub",
    "RRCHubActionsMixin",
    "RRCHubConnectionMixin",
    "RRCHubHistoryMixin",
    "RRCHubPacketHandlersMixin",
    "RRCManager",
    "RRCManagerPersistenceMixin",
    "RRCManagerRoomKeysMixin",
    "SLOW_CHANNEL_BPS",
    "_slow_connect_gate",
]
