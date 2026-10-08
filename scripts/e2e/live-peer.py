# SPDX-License-Identifier: 0BSD
"""Live e2e mesh peer for the Playwright stack.

Runs a real RNS node (TCP client of the e2e backend's TCPServerInterface),
announces lxmf.delivery, records inbound messages to peer_inbox.jsonl, relays
anything appended to peer_outbox.jsonl, and hosts a real RRC hub with a
lobby room. Control/state files live in the share dir passed as argv[3].
"""

import json
import os
import sys
import time

import RNS

config_dir, target_port, share_dir = sys.argv[1], int(sys.argv[2]), sys.argv[3]
inbox_path = os.path.join(share_dir, "peer_inbox.jsonl")
outbox_path = os.path.join(share_dir, "peer_outbox.jsonl")
ready_path = os.path.join(share_dir, "peer_ready.json")
hub_hash_path = os.path.join(share_dir, "peer_hub_hash")

conf = (
    "[reticulum]\n"
    "  enable_transport = False\n"
    "  share_instance = No\n"
    "  loglevel = 2\n"
    "[interfaces]\n"
    "  [[E2E Link]]\n"
    "    type = TCPClientInterface\n"
    "    enabled = Yes\n"
    "    target_host = 127.0.0.1\n"
    f"    target_port = {target_port}\n"
)
os.makedirs(config_dir, exist_ok=True)
with open(os.path.join(config_dir, "config"), "w") as f:
    f.write(conf)

RNS.Reticulum(configdir=config_dir, loglevel=RNS.LOG_DEBUG)

import LXMF

identity = RNS.Identity()
storage = os.path.join(config_dir, "lxmf_storage")
os.makedirs(storage, exist_ok=True)
router = LXMF.LXMRouter(storagepath=storage)
dest = router.register_delivery_identity(identity, display_name="e2e-peer")


def on_delivery(message):
    with open(inbox_path, "a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                {
                    "content": message.content_as_string(),
                    "title": message.title_as_string(),
                    "src": message.source_hash.hex(),
                    "dst": message.destination_hash.hex(),
                    "hash": message.hash.hex(),
                    "ts": time.time(),
                }
            )
            + "\n"
        )


router.register_delivery_callback(on_delivery)

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from meshchatx.src.backend.rrc.server import RRCHubServer
from meshchatx.src.backend.web_audio_bridge import install_hostless_lxst_audio


class _HubManagerStub:
    def _notify_change(self, *a, **k):
        pass

    def _notify_message(self, *a, **k):
        pass


hubs = []
for idx, (name, rooms) in enumerate(
    (
        ("E2E Hub", ["lobby", "test-room"]),
        ("E2E Hub B", ["lobby"]),
        ("E2E Hub C", ["lobby"]),
    )
):
    h = RRCHubServer(
        _HubManagerStub(),
        RNS.Identity(create_keys=True),
        name=name,
        announce=True,
    )
    h.configure_storage(os.path.join(config_dir, f"hub_storage_{idx}"))
    for room in rooms:
        h.register_room(room)
    h.start()
    hubs.append(h)

hub = hubs[0]

# Headless host has no audio devices. The hostless bridge swaps LXST
# LineSource/LineSink for no-op transports so Telephone works everywhere.
install_hostless_lxst_audio()
import LXST

phone = LXST.Telephone(identity, auto_answer=0.1)

with open(hub_hash_path, "w", encoding="utf-8") as f:
    f.write(hub.dest_hash.hex())
with open(ready_path, "w", encoding="utf-8") as f:
    json.dump(
        {
            "lxmf_dest": dest.hash.hex(),
            "hub_hash": hub.dest_hash.hex(),
            "hub_hashes": [h.dest_hash.hex() for h in hubs],
            "identity_hash": identity.hash.hex(),
        },
        f,
    )

# Adversarial announce storm: writing a count into share/peer.mode turns on a
# flood of synthetic rrc.hub announces. Mirrors the multi-hub churn that the
# rate limiting and announce caps exist to bound.
STORM_MODE_FILE = os.path.join(share_dir, "peer.mode")
storm_dests = []


def storm_count():
    try:
        with open(STORM_MODE_FILE, encoding="utf-8") as f:
            return int(f.read().strip() or "0")
    except Exception:
        return 0


def ensure_storm_dests(n):
    # The backend's announce classifier keys on the real rrc.hub aspect;
    # synthetic storm destinations must announce on it too or they only
    # fill the path table and skip the code path under test.
    while len(storm_dests) < n:
        storm_dests.append(
            RNS.Destination(
                RNS.Identity(create_keys=True),
                RNS.Destination.IN,
                RNS.Destination.SINGLE,
                "rrc",
                "hub",
            )
        )
    return storm_dests[:n]


outbox_pos = 0
pending = []
# Bounded lifetime only when explicitly requested. A self-killing peer
# silently deflates soak runs and late spec assertions.
deadline_s = float(os.environ.get("E2E_PEER_MAX_AGE", "0") or 0)
deadline = time.time() + deadline_s if deadline_s > 0 else None
while deadline is None or time.time() < deadline:
    dest.announce()
    try:
        for h in hubs:
            if h.destination is not None:
                h.destination.announce()
        phone.announce()
    except Exception:
        pass
    try:
        n = storm_count()
        if n:
            for d in ensure_storm_dests(n):
                d.announce()
    except Exception:
        pass
    try:
        if os.path.isfile(outbox_path):
            with open(outbox_path, encoding="utf-8") as f:
                f.seek(outbox_pos)
                lines = f.readlines()
                outbox_pos = f.tell()
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                try:
                    req = json.loads(line)
                except json.JSONDecodeError:
                    continue
                req["_deadline"] = time.time() + 120
                pending.append(req)
    except Exception:
        pass

    still_pending = []
    for req in pending:
        if time.time() > req["_deadline"]:
            continue
        try:
            peer_dest_hash = bytes.fromhex(req["dest"])
            # Nudge path discovery so a just-linked backend answers with an
            # announce instead of leaving recall permanently cold.
            if not RNS.Transport.has_path(peer_dest_hash):
                RNS.Transport.request_path(peer_dest_hash)
            peer_ident = RNS.Identity.recall(peer_dest_hash)
            if peer_ident is None:
                still_pending.append(req)
                continue
            peer_dest = RNS.Destination(
                peer_ident,
                RNS.Destination.OUT,
                RNS.Destination.SINGLE,
                "lxmf",
                "delivery",
            )
            msg = LXMF.LXMessage(
                peer_dest,
                dest,
                content=req.get("content") or "",
                title=req.get("title") or "",
                desired_method=LXMF.LXMessage.DIRECT,
            )
            router.handle_outbound(msg)
        except Exception:
            still_pending.append(req)
    pending = still_pending
    time.sleep(2)

RNS.exit(0)
