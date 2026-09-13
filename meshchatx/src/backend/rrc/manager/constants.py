# SPDX-License-Identifier: 0BSD

"""Constants and shared storage markers for RRC session management."""

import re
import threading

from meshchatx.src.backend.rrc import protocol as proto

DEFAULT_DEST_NAME = proto.DEFAULT_DEST_NAME
SLOW_CHANNEL_BPS = 300
_slow_connect_gate = threading.Semaphore(1)
BAD_KEY_MARKERS = ("bad key (+k)", "bad key")
FORCED_LEAVE_MARKERS = ("kicked from", "banned from", "banned (kline)")

HISTORY_DIR_NAME = "rrc_history"
HISTORY_FILENAME_SANITIZE_RE = re.compile(r"[^a-z0-9._-]+")

H_KIND = "k"
H_SRC = "s"
H_NICK = "n"
H_TEXT = "t"
H_TS = "ts"
H_MENTION = "m"
