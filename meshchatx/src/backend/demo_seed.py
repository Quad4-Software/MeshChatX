# SPDX-License-Identifier: 0BSD

"""Demo mode fixture: seed announces and conversations on first run.

Only runs when demo mode is active and the database is empty of messages, so
a real operator that switches demo mode on later keeps their own data. All
destination hashes are deterministic test vectors, not real identities.
"""

from __future__ import annotations

import base64
import hashlib
import time
from typing import TYPE_CHECKING

import RNS.vendor.umsgpack as msgpack

if TYPE_CHECKING:
    from meshchatx.meshchat import ReticulumMeshChat
    from meshchatx.src.backend.database import Database

def _hash(seed: str) -> str:
    return hashlib.sha256(f"meshchatx-demo:{seed}".encode()).hexdigest()[:32]


def _peer_app_data(name: str) -> str:
    return base64.b64encode(msgpack.packb([name, None, None])).decode("utf-8")


_PEERS = [
    {
        "seed": "ada",
        "name": "peer-04c2",
        "icon": ("account", "#ffffff", "#0d9488"),
        "messages": [
            (1, "Hey, are you seeing the new relay announce?", -1800),
            (0, "Yes, latency over LoRa is better than expected.", -1740),
            (1, "I pushed the antenna up another meter. RSSI improved a lot.", -1620),
            (0, "Nice. Can you still reach the ridge node?", -1500),
            (1, "Barely. I get about one announce every few minutes.", -1320),
            (0, "Send me a voice note when you are back in range.", -1140),
            (1, "Will do. Also try the offline map pack tonight.", -960),
            (0, "Already cached. The map holds up without any uplink.", -780),
        ],
    },
    {
        "seed": "rover",
        "name": "relay-north",
        "icon": ("wifi", "#ffffff", "#7c3aed"),
        "messages": [
            (1, "Copy. Rebroadcasting your announces.", -3600),
            (0, "Thanks. Path quality looks stable from here.", -3500),
        ],
    },
    {
        "seed": "meshbot",
        "name": "status-bot",
        "icon": ("robot", "#1a1a1a", "#f59e0b"),
        "messages": [
            (1, "Uptime 41 days. Heap at 62 percent.", -7200),
            (1, "Nodes within range: 7. Propagation: enabled.", -7140),
        ],
    },
]

_NODES = [
    {"seed": "nomad-node-a", "name": "nomad-pages-01", "aspect": "nomadnetwork.node"},
    {"seed": "nomad-node-b", "name": "nomad-files-02", "aspect": "nomadnetwork.node"},
]


def seed_demo_database(app: ReticulumMeshChat, database: Database) -> bool:
    """Insert demo fixture rows once. Returns True when rows were written.

    An existing message table means the operator already has real data, so the
    fixture is skipped. Demo containers start with an empty volume, which is
    the case this targets.
    """
    row = database.provider.fetchone("SELECT COUNT(*) AS c FROM lxmf_messages")
    if row and row["c"]:
        return False

    own_hash = app.identity.hash.hex() if getattr(app, "identity", None) else _hash("self")
    now = time.time()

    for peer in _PEERS:
        peer_hash = _hash(f"peer:{peer['seed']}")
        database.announces.upsert_announce(
            {
                "destination_hash": peer_hash,
                "aspect": "lxmf.delivery",
                "identity_hash": _hash(f"ident:{peer['seed']}"),
                "identity_public_key": None,
                "app_data": _peer_app_data(peer["name"]),
                "rssi": None,
                "snr": None,
                "quality": None,
            }
        )
        icon = peer["icon"]
        database.provider.execute(
            "INSERT OR REPLACE INTO lxmf_user_icons "
            "(destination_hash, icon_name, foreground_colour, background_colour, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))",
            (peer_hash, icon[0], icon[1], icon[2]),
        )
        for idx, (incoming, content, offset) in enumerate(peer["messages"]):
            database.messages.upsert_lxmf_message(
                {
                    "hash": _hash(f"msg:{peer['seed']}:{idx}"),
                    "source_hash": peer_hash if incoming else own_hash,
                    "destination_hash": own_hash if incoming else peer_hash,
                    "peer_hash": peer_hash,
                    "state": "delivered",
                    "progress": 1.0,
                    "is_incoming": incoming,
                    "method": "opportunistic",
                    "title": "",
                    "content": content,
                    "timestamp": now + offset,
                }
            )

    for node in _NODES:
        database.announces.upsert_announce(
            {
                "destination_hash": _hash(f"node:{node['seed']}"),
                "aspect": node["aspect"],
                "identity_hash": _hash(f"ident:{node['seed']}"),
                "identity_public_key": None,
                "app_data": base64.b64encode(node["name"].encode("utf-8")).decode("utf-8"),
                "rssi": None,
                "snr": None,
                "quality": None,
            }
        )

    return True
