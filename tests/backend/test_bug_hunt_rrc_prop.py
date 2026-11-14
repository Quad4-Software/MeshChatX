# SPDX-License-Identifier: 0BSD

"""Bug-hunt probes: each test pins a suspected defect; failures are bugs."""

import os
import threading
import time
from types import SimpleNamespace

import pytest

from meshchatx.src.backend.announce_manager import AnnounceManager
from meshchatx.src.backend.rrc import protocol as proto
from meshchatx.src.backend.rrc.manager import RRCHub, RRCManager


class FakeIdentity:
    def __init__(self, hash_bytes=b"\x01" * 16):
        self.hash = hash_bytes


def _manager(tmp_path):
    return RRCManager(identity=FakeIdentity(), storage_dir=str(tmp_path))


def _hub_with_room(tmp_path, room="general"):
    mgr = _manager(tmp_path)
    hub = mgr.add_hub(b"\xaa" * 16, name="t")
    hub.add_room(room)
    return mgr, hub


def _chat_msg(room, i, text):
    return proto.RRCMessage("msg", room, b"\x33" * 16, "peer", text, 1000 + i)


# ---------------------------------------------------------------------------
# Bug 1: history files for chat-only rooms grow without bound.
#
# _compact_history_files() is only invoked from _clean_history() when aged
# system/notice rows were actually removed. A room that only carries "msg"
# rows never triggers compaction, so the on-disk log grows past
# HISTORY_FILE_MAX_BYTES forever even though the in-memory buffer is capped.
# ---------------------------------------------------------------------------


def test_history_file_stays_bounded_for_chat_only_room(tmp_path):
    mgr, hub = _hub_with_room(tmp_path)
    big = "x" * 200_000
    for i in range(50):
        hub._record_message(_chat_msg("general", i, f"{i}:" + big))

    # Force several clean passes; nothing is old enough to reap.
    for _ in range(3):
        hub._last_history_clean = 0
        hub._clean_history()

    path = mgr._history_path(hub, "general")
    size = os.path.getsize(path)
    # In-memory buffer is correctly capped; the file must be too.
    assert size <= RRCHub.HISTORY_FILE_MAX_BYTES + 300_000, (
        f"history file grew to {size} bytes with no compaction trigger"
    )


# ---------------------------------------------------------------------------
# Bug 1b: once the log exceeds the 9 MiB load window, the newest records are
# beyond the read prefix and are silently lost on restart.
# ---------------------------------------------------------------------------


def test_history_reload_keeps_newest_messages(tmp_path):
    mgr, hub = _hub_with_room(tmp_path)
    big = "x" * 200_000
    for i in range(50):
        hub._record_message(_chat_msg("general", i, f"{i}:" + big))
    mgr.save()

    mgr2 = _manager(tmp_path)
    mgr2.load()
    assert len(mgr2.hubs) == 1
    texts = [m.text for m in mgr2.hubs[0].get_messages("general")]
    assert any(t.startswith("49:") for t in texts), (
        "newest history record was lost: file tail is past the read window"
    )


# ---------------------------------------------------------------------------
# Bug 2: a stale (already-seen) envelope id with no room makes
# _bump_duplicate_by_mid scan EVERY room buffer while holding hub._lock.
# _handle_chat marks the mid seen before validating the body, so a single
# envelope with a non-string body mints a permanent "seen but unrecorded"
# mid; each replay then pays a full-table scan. Remote-triggerable CPU DoS.
# ---------------------------------------------------------------------------


class _CountingList(list):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.iterated = 0

    def __iter__(self):
        self.iterated += 1
        return super().__iter__()


def test_stale_envelope_replay_does_not_scan_all_rooms(tmp_path):
    mgr = _manager(tmp_path)
    hub = mgr.add_hub(b"\xaa" * 16, name="t")
    # Populate several ephemeral room buffers.
    for r in ("r1", "r2", "r3", "r4"):
        for i in range(25):
            hub._record_message(_chat_msg(r, i, f"{r}-{i}"))
    counting = {}
    for r, buf in hub.messages.items():
        cl = _CountingList(buf)
        hub.messages[r] = cl
        counting[r] = cl
    total_rooms = len(hub.messages)
    assert total_rooms >= 4

    # Envelope 1: valid mid, non-string body -> mid marked seen, msg dropped.
    env = proto.make_envelope(
        proto.T_MSG, src=b"\x44" * 16, room=None, body=12345, mid=b"\x55" * 8
    )
    blob = proto.encode(env)
    hub._on_packet(blob)
    # Envelope 2 (replay): stale mid -> _bump_duplicate_by_mid(mid, None).
    hub._on_packet(blob)

    scanned = sum(cl.iterated for cl in counting.values())
    # The bump should only scan when a room is known; with room=None it must
    # not iterate every room buffer under the hub lock.
    assert scanned < total_rooms, (
        f"stale replay scanned all {scanned}/{total_rooms} room buffers"
    )


# ---------------------------------------------------------------------------
# Bug 3: executable pages have no output cap and no concurrency limit.
# serve_page_content returns whatever the script writes to stdout; a peer
# can pull hundreds of MB per request and spawn unbounded subprocesses.
# ---------------------------------------------------------------------------


def _exec_node(tmp_path, script_body):
    import meshchatx.src.backend.page_node as pn

    for d in ("pages", "files", "media_cache"):
        os.makedirs(os.path.join(tmp_path, d), exist_ok=True)
    node = pn.PageNode(
        "n1", "t", str(tmp_path), executable_pages_enabled=True
    )
    node.pages_dir = os.path.join(tmp_path, "pages")
    node.files_dir = os.path.join(tmp_path, "files")
    node.media_cache_dir = os.path.join(tmp_path, "media_cache")
    script = os.path.join(node.pages_dir, "gen.mu")
    with open(script, "w") as f:
        f.write(script_body)
    os.chmod(script, 0o755)
    node._executable_page_names.add("gen.mu")
    return node


def test_executable_page_output_is_bounded(tmp_path):
    node = _exec_node(
        tmp_path,
        "#!/bin/sh\nhead -c 67108864 /dev/zero | tr '\\0' 'A'\n",
    )
    out = node.serve_page_content("gen.mu")
    assert out is not None
    assert len(out) <= 8 * 1024 * 1024, (
        f"page script stdout not capped: served {len(out)} bytes"
    )


def test_executable_page_requests_are_concurrency_limited(tmp_path, monkeypatch):
    import meshchatx.src.backend.page_node as pn

    node = _exec_node(tmp_path, "#!/bin/sh\nsleep 5\n")
    cur = [0]
    peak = [0]
    lock = threading.Lock()

    def fake_run(*args, **kwargs):
        with lock:
            cur[0] += 1
            peak[0] = max(peak[0], cur[0])
        try:
            time.sleep(0.05)
            return SimpleNamespace(stdout=b"x")
        finally:
            with lock:
                cur[0] -= 1

    monkeypatch.setattr(pn.subprocess, "run", fake_run)
    threads = [
        threading.Thread(target=node.serve_page_content, args=("gen.mu",))
        for _ in range(8)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert peak[0] <= 2, f"{peak[0]} concurrent page subprocesses, no limit"


# ---------------------------------------------------------------------------
# Bug 4: _file_access_grants entries are only removed inside
# _check_file_access. A peer that only fetches pages (never files/media)
# grows the dict without bound; expired entries are never reaped.
# ---------------------------------------------------------------------------


def test_file_access_grants_do_not_accumulate(tmp_path):
    import meshchatx.src.backend.page_node as pn

    for d in ("pages", "files", "media_cache"):
        os.makedirs(os.path.join(tmp_path, d), exist_ok=True)
    node = pn.PageNode("n1", "t", str(tmp_path))
    node.pages_dir = os.path.join(tmp_path, "pages")
    node.files_dir = os.path.join(tmp_path, "files")
    node.media_cache_dir = os.path.join(tmp_path, "media_cache")

    class FakeIdent:
        hash = b"\x09" * 16

    for i in range(200):
        node._grant_file_access(f"link-{i}", FakeIdent(), ttl=0)
    time.sleep(0.01)
    # No _check_file_access call happens, so expiry is never evaluated.
    assert len(node._file_access_grants) == 0, (
        f"{len(node._file_access_grants)} expired grants retained"
    )


# ---------------------------------------------------------------------------
# Bug 7: the hub server decodes packets with no size cap. The client side
# (RRCHub._on_packet) rejects data > MAX_PACKET_BYTES before proto.decode;
# RRCHubServer._on_packet decodes whatever the link delivers first.
# ---------------------------------------------------------------------------


def test_hub_server_rejects_oversized_wire_packets():
    from meshchatx.src.backend.rrc import server as rrc_server
    from meshchatx.src.backend.rrc.manager import MAX_PACKET_BYTES

    srv = rrc_server.RRCHubServer(None, FakeIdentity())
    calls = []
    orig = rrc_server.proto.decode

    def spy(data):
        calls.append(len(data))
        return orig(data)

    rrc_server.proto.decode = spy
    try:
        blob = proto.encode({"pad": "A" * (MAX_PACKET_BYTES + 16)})
        srv._on_packet(object(), blob)
    finally:
        rrc_server.proto.decode = orig
    assert not calls, (
        f"hub server ran CBOR decode on {calls} byte packet(s) over "
        f"MAX_PACKET_BYTES={MAX_PACKET_BYTES}"
    )


# ---------------------------------------------------------------------------
# Bug 5: AnnounceManager._reload_peer_sets returns early (without stamping
# _peer_sets_loaded_at) when the block list read fails, so every inbound
# announce re-runs the contacts/favourites/DISTINCT-peer_hash queries.
# ---------------------------------------------------------------------------


def test_announce_peer_sets_reload_is_not_repeated_on_blocklist_failure(
    db, monkeypatch
):
    def boom():
        raise RuntimeError("blocked_destinations unavailable")

    monkeypatch.setattr(db.misc, "get_blocked_destinations", boom)

    calls = {"n": 0}
    orig = db.provider.fetchall

    def spy(sql, params=()):
        if "lxmf_messages" in str(sql):
            calls["n"] += 1
        return orig(sql, params)

    monkeypatch.setattr(db.provider, "fetchall", spy)

    mgr = AnnounceManager(db)
    mgr.classify_announce("ab" * 32)
    mgr.classify_announce("ab" * 32)
    mgr.classify_announce("cd" * 32)
    assert calls["n"] == 1, (
        f"peer-set rebuild ran {calls['n']} times on persistent blocklist failure"
    )


# ---------------------------------------------------------------------------
# Bug 6: _probe_propagation_sync treats ANY router state churn as proof the
# probed node completed a sync. A concurrent manual sync to a different
# peer satisfies the state machine and the unverified node is recorded as
# successful and promoted to preferred.
# ---------------------------------------------------------------------------


class _ScriptedRouter:
    """Router whose transfer state plays back an unrelated sync."""

    def __init__(self, states):
        from LXMF.LXMRouter import LXMRouter

        self._script = list(states)
        self._state = states[-1]
        self.PR_IDLE = LXMRouter.PR_IDLE
        self.PR_COMPLETE = LXMRouter.PR_COMPLETE
        self.outbound = None
        self.requests = []

    @property
    def propagation_transfer_state(self):
        if self._script:
            self._state = self._script.pop(0)
        return self._state

    @propagation_transfer_state.setter
    def propagation_transfer_state(self, value):
        self._state = value

    def set_outbound_propagation_node(self, dest):
        self.outbound = dest

    def get_outbound_propagation_node(self):
        return self.outbound

    def request_messages_from_propagation_node(self, identity, max_messages=None):
        # The request is swallowed: no link, no transfer to the probed node.
        # An unrelated in-flight sync drives the state machine instead.
        self.requests.append((identity, max_messages))


class _Ctx:
    def __init__(self, router):
        self.message_router = router
        self.identity = FakeIdentity()
        self.running = True


class _App:
    def __init__(self):
        self.reticulum = None
        self.stopped = []

    def stop_propagation_node_sync(self, context=None):
        self.stopped.append(context)


@pytest.mark.asyncio
async def test_propagation_probe_rejects_unrelated_transfer():
    from LXMF.LXMRouter import LXMRouter

    from meshchatx.src.backend.auto_propagation_manager import (
        AutoPropagationManager,
    )

    router = _ScriptedRouter(
        [
            LXMRouter.PR_IDLE,  # settle read 1
            LXMRouter.PR_IDLE,  # settle read 2 (== COMPLETE check)
            LXMRouter.PR_IDLE,  # probe loop 1 iter 1: still idle
            LXMRouter.PR_REQUEST_SENT,  # loop 1 iter 2: left idle
            LXMRouter.PR_COMPLETE,  # loop 2 iter 1: "success"
        ]
    )
    ctx = _Ctx(router)
    app = _App()

    class _Cfg:
        def get(self, key, default_value=None):
            return default_value

    class _CfgWrap:
        def get(self, key, default_value=None):
            return default_value

        def set(self, key, value):
            pass

    mgr = AutoPropagationManager.__new__(AutoPropagationManager)
    mgr.app = app
    mgr.context = ctx
    mgr.config = _CfgWrap()
    mgr.database = None
    mgr.running = False
    mgr._check_interval = 300
    mgr._memory = {}

    node_hex = "ab" * 16
    result = await mgr._probe_propagation_sync(node_hex)
    # The probe must not report success: the completing transfer was never
    # shown to target the probed destination.
    assert result is False, (
        "probe verified a node whose request never produced a matching transfer"
    )
