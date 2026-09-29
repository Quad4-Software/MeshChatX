# SPDX-License-Identifier: 0BSD
"""Fault-injection tests across backend sections.

Each test feeds malformed input or makes a dependency raise, then asserts
the component absorbs the fault: no crash, no wedged state, no orphaned
timers or worker threads.
"""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
import threading
import time
from unittest.mock import MagicMock, patch

import pytest
import RNS

from meshchatx.src.backend import rns_link_manager
from meshchatx.src.backend.announce_handler import AnnounceHandler
from meshchatx.src.backend.auto_resend_guard import (
    fields_with_auto_resend_count,
    read_auto_resend_count,
)
from meshchatx.src.backend.crawler_manager import CrawlerManager
from meshchatx.src.backend.rrc import protocol as proto
from meshchatx.src.backend.rrc.manager import RRCHub, RRCManager


class FakeIdentity:
    def __init__(self, hash_bytes=b"\x00" * 16):
        self.hash = hash_bytes

    def get_private_key(self):
        return b"\x01" * 32


def make_manager(tmp_path):
    return RRCManager(identity=FakeIdentity(), storage_dir=str(tmp_path))


def make_hub(tmp_path, i=1):
    manager = make_manager(tmp_path)
    return manager.add_hub(bytes([i & 0xFF]) + b"\x00" * 15)


def cancel_hub_timer(hub):
    if hub._reconnect_timer is not None:
        hub._reconnect_timer.cancel()
        hub._reconnect_timer = None


# ---------------------------------------------------------------- RRC wire


def test_rrc_packet_garbage_is_dropped(tmp_path):
    hub = make_hub(tmp_path)
    for payload in (
        b"",
        b"\x00" * 512,
        os.urandom(4096),
        b"\xff" * 65536,
        proto.encode([1, 2, 3]),
        proto.encode("not a dict"),
        proto.encode({"unexpected": "dict without type"}),
        proto.encode({proto.K_T: 9999}),
        proto.encode({proto.K_T: "string type"}),
    ):
        hub._on_packet(payload)
    assert hub.messages == {}
    assert hub.notices == []
    assert not hub.welcomed


def test_rrc_malformed_known_types_do_not_raise(tmp_path):
    hub = make_hub(tmp_path)
    src = b"\x11" * 16
    malformed = [
        # WELCOME whose limits are not ints must not raise into RNS callbacks
        proto.make_envelope(
            proto.T_WELCOME, src, body={proto.B_WELCOME_LIMITS: {4: "x"}}
        ),
        proto.make_envelope(
            proto.T_WELCOME, src, body={proto.B_WELCOME_LIMITS: {4: {}}}
        ),
        proto.make_envelope(proto.T_WELCOME, src, body="nope"),
        proto.make_envelope(proto.T_MSG, src, room=123, body="hi"),
        proto.make_envelope(proto.T_MSG, src, room="lobby"),
        proto.make_envelope(proto.T_NOTICE, src, room="lobby", body=[1, 2]),
        proto.make_envelope(proto.T_JOINED, src, room="lobby", body="not a list"),
        proto.make_envelope(proto.T_JOINED, src, room="   ", body=[b"\xaa" * 16]),
        proto.make_envelope(proto.T_PONG, src, body="not bytes"),
        proto.make_envelope(proto.T_ERROR, src, body=12345),
    ]
    for env in malformed:
        hub._on_packet(proto.encode(env))
    assert isinstance(hub.messages, dict)


def test_rrc_handler_exception_is_contained(tmp_path):
    """A raising packet handler must not propagate out of _on_packet."""
    hub = make_hub(tmp_path)

    def boom(_hub, _env):
        raise RuntimeError("injected handler failure")

    monkey = RRCHub._PACKET_HANDLERS
    saved = dict(monkey)
    try:
        monkey[proto.T_MSG] = boom
        hub._on_packet(
            proto.encode(
                proto.make_envelope(
                    proto.T_MSG, src=b"\x11" * 16, room="lobby", body="hi"
                )
            )
        )
    finally:
        RRCHub._PACKET_HANDLERS.clear()
        RRCHub._PACKET_HANDLERS.update(saved)


def test_rrc_double_link_close_yields_single_reconnect(tmp_path):
    hub = make_hub(tmp_path)
    hub.auto_reconnect = True
    try:
        link = MagicMock()
        hub._on_closed(link)
        # The same dead link reporting close twice (watchdog teardown after
        # the RNS callback already fired) must not double-count the backoff.
        hub._on_closed(link)
        assert hub._reconnect_attempts == 1
        assert hub._reconnect_timer is not None
    finally:
        cancel_hub_timer(hub)


def test_rrc_distinct_link_closes_count_backoff(tmp_path):
    hub = make_hub(tmp_path)
    hub.auto_reconnect = True
    try:
        hub._on_closed(MagicMock())
        hub._on_closed(MagicMock())
        assert hub._reconnect_attempts == 2
        assert hub._reconnect_timer is not None
    finally:
        cancel_hub_timer(hub)


def test_rrc_connect_worker_exception_schedules_backoff(tmp_path, monkeypatch):
    hub = make_hub(tmp_path)
    hub.auto_reconnect = True
    monkeypatch.setattr(
        hub.manager,
        "find_local_server",
        lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    try:
        hub._connect_worker()
        # The failure is contained: the hub schedules a backoff retry rather
        # than propagating the exception or leaving the worker hung.
        assert hub._reconnect_timer is not None
        assert hub._reconnect_attempts == 1
    finally:
        cancel_hub_timer(hub)


def test_rrc_disconnect_cancels_pending_reconnect(tmp_path):
    hub = make_hub(tmp_path)
    hub.auto_reconnect = True
    hub._on_closed(MagicMock())
    assert hub._reconnect_timer is not None
    hub.disconnect()
    assert hub._reconnect_timer is None
    assert hub._reconnect_attempts == 0
    # The cancelled timer must never fire a connect.
    fired = []
    monkey_fire = hub._fire_reconnect
    hub._fire_reconnect = lambda: fired.append(1)
    time.sleep(0.05)
    hub._fire_reconnect = monkey_fire
    assert fired == []


def test_rrc_announce_flood_stays_rate_limited(tmp_path):
    """A hub announcing in a tight loop cannot pin retries at the fast tier."""
    hub = make_hub(tmp_path)
    hub.auto_reconnect = True
    hub.status = RRCHub.STATUS_DISCONNECTED
    hub._reconnect_attempts = 9
    try:
        for _ in range(2000):
            hub.note_hub_announce()
        # Only the first call inside the window may reset the counter.
        assert hub._reconnect_attempts <= 1
    finally:
        cancel_hub_timer(hub)


def test_rrc_save_survives_concurrent_mutation(tmp_path):
    manager = make_manager(tmp_path)
    errors = []
    stop = threading.Event()

    def writer():
        i = 0
        while not stop.is_set():
            manager.add_hub(bytes([i & 0xFF, (i >> 8) & 0xFF]) + b"\xab" * 14)
            i += 1

    def reader():
        while not stop.is_set():
            manager.save()

    threads = [
        threading.Thread(target=writer, daemon=True),
        threading.Thread(target=reader, daemon=True),
        threading.Thread(target=reader, daemon=True),
    ]
    try:
        for t in threads:
            t.start()
        time.sleep(0.5)
    finally:
        stop.set()
        for t in threads:
            t.join(timeout=5)
        errors.extend("thread did not exit" for t in threads if t.is_alive())
    assert not errors

    path = manager._store_path()
    if os.path.isfile(path):
        decoded = proto.decode(open(path, "rb").read())
        assert isinstance(decoded, dict)
        assert isinstance(decoded.get("hubs"), list)


def test_rrc_load_corrupt_store_yields_empty(tmp_path):
    manager = make_manager(tmp_path)
    path = manager._store_path()
    with open(path, "wb") as f:
        f.write(b"\xde\xad\xbe\xef not cbor")
    manager.load()
    assert manager.hubs == []


def test_rrc_load_truncated_store_yields_empty(tmp_path):
    manager = make_manager(tmp_path)
    manager.add_hub(b"\x01" + b"\x00" * 15, name="x")
    path = manager._store_path()
    data = open(path, "rb").read()
    with open(path, "wb") as f:
        f.write(data[: len(data) // 2])
    reloaded = RRCManager(identity=FakeIdentity(), storage_dir=str(tmp_path))
    reloaded.load()
    assert reloaded.hubs == []


# -------------------------------------------------------------- page node


@pytest.fixture
def mock_rns():
    with patch("meshchatx.src.backend.page_node.RNS") as mock:
        mock_identity = MagicMock()
        mock_identity.hash = b"\x01" * 16
        mock_identity.get_public_key.return_value = b"\x02" * 64

        mock_destination = MagicMock()
        mock_destination.hash = b"\x03" * 16

        mock.Identity.return_value = mock_identity
        mock.Identity.from_file.return_value = mock_identity
        mock.Destination.return_value = mock_destination
        mock.Destination.IN = 1
        mock.Destination.SINGLE = 0
        mock.Destination.ALLOW_ALL = 0xFF
        mock.Transport = MagicMock()
        mock.vendor = MagicMock()
        mock.vendor.platformutils = MagicMock()
        mock.vendor.platformutils.is_windows.return_value = False

        yield mock, mock_identity, mock_destination


def _make_node(node_dir, mock_rns):
    from meshchatx.src.backend.page_node import PageNode

    _, mock_identity, _ = mock_rns
    return PageNode(
        node_id="fault-node",
        name="Fault Node",
        base_dir=node_dir,
        identity=mock_identity,
    )


def test_page_rescan_survives_pages_dir_replaced_by_file(tmp_path, mock_rns):
    node = _make_node(str(tmp_path), mock_rns)
    node.setup()
    # Replace the pages dir with a plain file mid-run; rescan must not crash.
    os.rmdir(node.pages_dir)
    with open(node.pages_dir, "w") as f:
        f.write("not a directory")
    node._rescan_content()
    assert node.list_pages() == []
    node.teardown()


def test_page_rescan_survives_when_not_running(tmp_path, mock_rns):
    node = _make_node(str(tmp_path), mock_rns)
    node.setup()
    node.teardown()
    node._rescan_content()
    assert node.list_pages() == []


def test_page_rescan_skips_non_file_entries(tmp_path, mock_rns):
    node = _make_node(str(tmp_path), mock_rns)
    node.setup()
    # A directory inside pages/ must not produce a servable page entry.
    os.mkdir(os.path.join(node.pages_dir, "nested.mu"))
    node._rescan_content()
    assert "nested.mu" not in [p["name"] for p in node.list_pages()]
    node.teardown()


# ---------------------------------------------------------------- crawler


class _Cfg:
    class Int:
        def __init__(self, v):
            self._v = v

        def get(self):
            return self._v

    crawler_max_depth = Int(2)
    crawler_max_pages_per_node = Int(20)
    crawler_max_hops = Int(4)
    crawler_max_rtt_ms = Int(2500)
    crawler_requests_per_day_per_node = Int(1)
    crawler_refresh_days = Int(30)


def test_crawler_queue_rejects_garbage_dests(db):
    mgr = CrawlerManager(db, _Cfg())
    for dest in (None, "", "not-hex-at-all", "ab" * 15, "ab" * 17, " " * 32):
        assert mgr.queue_if_allowed(dest, "/page/index.mu") is False


def test_crawler_queue_tolerates_odd_paths(db):
    mgr = CrawlerManager(db, _Cfg())
    for dest, path in (
        ("ab" * 16, None),
        ("ab" * 16, ""),
        ("ab" * 16, "not/a/page"),
        ("zz" * 16, "/page/index.mu"),
    ):
        assert mgr.queue_if_allowed(dest, path) in (True, False)


def test_crawler_queue_db_failure_propagates_cleanly(db):
    """A wedged DB raises out of queue_if_allowed.

    Callers (crawler_loop) catch per-iteration. Assert the failure does
    not wedge the manager.
    """
    mgr = CrawlerManager(db, _Cfg())
    orig = db.misc.upsert_crawl_task

    def boom(*_a, **_k):
        raise RuntimeError("db wedged")

    db.misc.upsert_crawl_task = boom
    try:
        with pytest.raises(RuntimeError):
            mgr.queue_if_allowed("cd" * 16, "/page/index.mu", force=True)
    finally:
        db.misc.upsert_crawl_task = orig
    # After the fault clears the manager still works.
    assert mgr.queue_if_allowed("zz" * 16, "/page/index.mu") in (True, False)


# --------------------------------------------------------- auto resend


def test_auto_resend_count_reads_garbage_as_zero():
    for blob in (
        None,
        b"\xff\xfe binary",
        "not json at all",
        '{"_mcx_auto_resend_count": "abc"}',
        '{"_mcx_auto_resend_count": -7}',
        '{"_mcx_auto_resend_count": null}',
        '{"_mcx_auto_resend_count": [1]}',
        42,
        ["list", "not", "dict"],
    ):
        assert read_auto_resend_count(blob) == 0


def test_auto_resend_count_roundtrip_from_garbage():
    fields = fields_with_auto_resend_count("corrupt blob \x00\x01", 2)
    assert read_auto_resend_count(fields) == 2


# ------------------------------------------------------- announce handler


def test_announce_handler_swallows_callback_errors():
    calls = []

    def raising(*_args):
        calls.append(1)
        raise RuntimeError("injected announce callback failure")

    handler = AnnounceHandler("lxmf.delivery", raising)
    handler.received_announce(
        b"\x00" * 16,
        MagicMock(),
        b"appdata",
        b"\x01" * 32,
    )
    assert calls == [1]


# ---------------------------------------------------------- RRC hub server


class _FakeLink:
    def __init__(self, identity):
        self._identity = identity

    def get_remote_identity(self):
        return self._identity


class _FakeManager:
    def __init__(self):
        self.changes = 0
        self.history_per_room_cap = 0
        self.identity = FakeIdentity(b"\x22" * 16)

    def _notify_change(self, hub=None):
        self.changes += 1

    def _notify_messages(self, hub, msg):
        pass

    def active_room_for(self, hub):
        return None

    def save(self):
        pass


def _make_server():
    from meshchatx.src.backend.rrc.server import RRCHubServer

    return RRCHubServer(_FakeManager(), FakeIdentity(bytes(range(16))), name="T")


def test_rrc_server_garbage_packets_do_not_crash():
    server = _make_server()
    link = _FakeLink(FakeIdentity(b"\xaa" * 16))
    for payload in (
        b"",
        os.urandom(1024),
        proto.encode([1, 2]),
        proto.encode("junk"),
        proto.encode({proto.K_T: 9999}),
    ):
        server._on_packet(link, payload)


def test_rrc_server_handler_fault_is_contained():
    """A handler exception inside _route must not escape _on_packet."""
    from meshchatx.src.backend.rrc.server import _Session

    server = _make_server()
    link = _FakeLink(FakeIdentity(b"\xbb" * 16))
    sess = _Session()
    sess.peer = link._identity.hash
    sess.welcomed = True
    server._sessions[link] = sess

    def boom(*_a, **_k):
        raise RuntimeError("injected route failure")

    saved = server._handle_join
    server._handle_join = boom
    try:
        env = proto.make_envelope(proto.T_JOIN, src=sess.peer, room="lobby")
        server._on_packet(link, proto.encode(env))
    finally:
        server._handle_join = saved
    # Session survives; hub keeps accepting packets.
    assert link in server._sessions


def test_rrc_server_unwelcomed_session_cannot_join():
    """Packets other than HELLO before welcome must be ignored, not raise."""
    from meshchatx.src.backend.rrc.server import _Session

    server = _make_server()
    link = _FakeLink(FakeIdentity(b"\xcc" * 16))
    sess = _Session()
    sess.peer = link._identity.hash
    sess.welcomed = False
    server._sessions[link] = sess
    env = proto.make_envelope(proto.T_JOIN, src=sess.peer, room="lobby")
    server._on_packet(link, proto.encode(env))
    assert "lobby" not in sess.rooms


# --------------------------------------------------------- link cache


class _ExplodingLink:
    status = 99  # never equals RNS.Link.ACTIVE

    def teardown(self):
        raise RuntimeError("teardown exploded")


def test_link_sweep_survives_teardown_errors():
    key = ("aspect.fault", b"\x09" * 16)
    rns_link_manager.rns_cached_links[key] = _ExplodingLink()
    rns_link_manager._rns_link_last_used[key] = 0.0
    rns_link_manager.sweep_stale_links()
    assert key not in rns_link_manager.rns_cached_links
    assert key not in rns_link_manager._rns_link_last_used


def test_link_clear_all_survives_teardown_errors():
    key = ("aspect.fault2", b"\x0a" * 16)
    rns_link_manager.rns_cached_links[key] = _ExplodingLink()
    removed = rns_link_manager.clear_all_cached_links()
    assert removed >= 1
    assert key not in rns_link_manager.rns_cached_links


def test_cached_link_evicted_when_not_active():
    class DeadLink:
        status = 0  # CLOSED-ish, anything but ACTIVE

    key = ("aspect.dead", b"\x0b" * 16)
    rns_link_manager.rns_cached_links[key] = DeadLink()
    rns_link_manager._rns_link_last_used[key] = time.time()
    assert rns_link_manager.get_cached_active_link(*key) is None
    assert key not in rns_link_manager.rns_cached_links


def test_run_async_completed_future_never_deadlocks(tmp_path):
    """Regression: run_async held _futures_lock across add_done_callback.

    When the scheduled coroutine completes before add_done_callback runs,
    _forget_future fires inline and re-acquires the non-reentrant lock,
    self-deadlocking the caller. Every later producer then parks behind it,
    freezing the main loop. Probe in a subprocess so a regression leaves the
    suite unpoisoned.
    """
    script = textwrap.dedent(
        """
        import asyncio
        import concurrent.futures

        from meshchatx.src.backend.async_utils import AsyncUtils

        class FakeLoop:
            def is_running(self):
                return True

        fut = concurrent.futures.Future()
        fut.set_result("done")

        def fake_schedule(coro, loop):
            coro.close()  # created but never awaited under the stub
            return fut

        asyncio.run_coroutine_threadsafe = fake_schedule
        AsyncUtils.main_loop = FakeLoop()

        async def noop():
            return None

        for _ in range(100):
            AsyncUtils.run_async(noop())
        print("no deadlock")
        """,
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert "no deadlock" in result.stdout


def test_identity_public_key_reconstruction_matches_identity_hash():
    """Pin the RNS API contract used by telephony resolve_identity.

    load_public_key(pubkey) must reproduce the original identity hash.
    from_bytes() takes a PRIVATE key and silently produces a different
    identity when fed a pubkey, which is exactly the bug this guards.
    """
    ident = RNS.Identity()
    pk = ident.get_public_key()

    clone = RNS.Identity(create_keys=False)
    assert clone.load_public_key(pk) is True
    assert clone.hash == ident.hash
