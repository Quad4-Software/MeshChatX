# SPDX-License-Identifier: 0BSD

"""Regression tests for the 2026 bug-hunt fixes.

Each test pins a confirmed defect that could otherwise come back silently.
"""

from __future__ import annotations

import io
import time
import zipfile

import pytest

from meshchatx.src.backend.rrc import protocol as proto
from meshchatx.src.backend.rrc.manager import RRCManager
from meshchatx.src.backend.rrc.server import PRE_WELCOME_TIMEOUT_S, RRCHubServer

HUB_HASH = bytes(range(16))


class FakeIdentity:
    def __init__(self, hash_bytes):
        self.hash = hash_bytes


class FakeLink:
    def __init__(self, identity):
        self._identity = identity
        self.torndown = False

    def get_remote_identity(self):
        return self._identity

    def teardown(self):
        self.torndown = True

    def set_packet_callback(self, cb):
        self._packet_cb = cb

    def set_link_closed_callback(self, cb):
        self._closed_cb = cb

    def set_remote_identified_callback(self, cb):
        self._identified_cb = cb


class FakeManager:
    def __init__(self):
        self.identity = FakeIdentity(b"\x22" * 16)
        self.history_per_room_cap = 0
        self.filter_loaded_history = False
        self._active_hub = None
        self._active_room = None
        self.saved = 0

    def get_nickname(self):
        return None

    def get_name_for_identity_hash(self, _h):
        return None

    def save(self):
        self.saved += 1

    def _notify_change(self, hub=None):
        pass

    def _notify_messages(self, hub, msg):
        pass

    def is_fatal_join_error(self, text):
        return False

    def is_forced_leave_error(self, text):
        return "kline" in text or "banned" in text

    def is_bad_key_error(self, text):
        return False

    def forget_room_key(self, hub, room):
        pass


def make_server():
    return RRCHubServer(FakeManager(), FakeIdentity(HUB_HASH), name="Hub")


def make_client_hub(tmp_path):
    manager = RRCManager(
        identity=FakeIdentity(b"\x11" * 16),
        storage_dir=str(tmp_path),
    )
    return manager.add_hub(HUB_HASH, name="Client")


# --- RRC: stale-link close must not nuke the live session --------------------


def test_stale_link_close_does_not_clear_session(tmp_path):
    hub = make_client_hub(tmp_path)
    old_link = FakeLink(FakeIdentity(b"\xaa" * 16))
    new_link = FakeLink(FakeIdentity(b"\xbb" * 16))
    hub.link = old_link
    hub.welcomed = True
    hub.rooms.add("lobby")

    # A reconnect replaced the link; the old link's late close arrives after.
    hub.link = new_link
    hub._on_closed(old_link)

    assert hub.link is new_link
    assert "lobby" in hub.rooms


def test_current_link_close_clears_session(tmp_path):
    hub = make_client_hub(tmp_path)
    link = FakeLink(FakeIdentity(b"\xaa" * 16))
    hub.link = link
    hub.welcomed = True
    hub.auto_reconnect = False
    hub.rooms.add("lobby")

    hub._on_closed(link)

    assert hub.link is None
    assert not hub.welcomed
    # Room membership is retained for reconnect; session state is cleared.
    assert not hub.members


def test_welcome_timeout_teardown_does_not_double_reconnect(tmp_path):
    hub = make_client_hub(tmp_path)
    hub.auto_reconnect = True
    link = FakeLink(FakeIdentity(b"\xaa" * 16))
    hub.link = link
    calls = []
    hub._schedule_reconnect = lambda: calls.append(1)
    hub._maybe_schedule_reconnect_after_failed_connect = lambda: calls.append(2)

    hub._fail_welcome_timeout()
    # The teardown callback arriving late must not schedule a second reconnect.
    hub._on_closed(link)
    assert calls.count(1) == 0
    assert calls.count(2) == 1


def test_phantom_joined_does_not_create_room(tmp_path):
    hub = make_client_hub(tmp_path)
    hub.welcomed = True
    hub._handle_joined(
        proto.make_envelope(
            proto.T_JOINED,
            src=HUB_HASH,
            room="neverjoined",
            body=[b"\xaa" * 16],
            nick="eve",
        ),
    )
    assert "neverjoined" not in hub.rooms
    assert "neverjoined" not in hub.members


def test_roomless_forced_leave_preserves_history(tmp_path):
    hub = make_client_hub(tmp_path)
    hub.welcomed = True
    hub.rooms.add("lobby")
    hub.members["lobby"] = {b"\xaa" * 16}
    deleted = []
    hub._delete_history = lambda room: deleted.append(room)

    hub._handle_error(
        proto.make_envelope(
            proto.T_ERROR,
            src=HUB_HASH,
            body="banned (kline)",
        ),
    )
    # Membership cleared, but on-disk history survives a bare forced-leave.
    assert "lobby" not in hub.rooms
    assert deleted == []


def test_resource_expectations_expire(tmp_path):
    hub = make_client_hub(tmp_path)
    hub._resource_expectations[b"old"] = {
        "kind": "text",
        "size": 1,
        "sha256": None,
        "encoding": "utf-8",
        "room": None,
        "expires": time.monotonic() - 1,
    }
    body = {
        proto.B_RES_ID: b"\x01" * 16,
        proto.B_RES_KIND: "text",
        proto.B_RES_SIZE: 10,
    }
    hub._handle_resource_envelope(
        proto.make_envelope(proto.T_MSG, src=HUB_HASH, body=body),
    )
    assert b"old" not in hub._resource_expectations
    assert b"\x01" * 16 in hub._resource_expectations


# --- RRC server: pre-HELLO sessions get reaped --------------------------------


def test_pre_hello_sessions_reaped():
    server = make_server()
    link = FakeLink(FakeIdentity(b"\xaa" * 16))
    server._on_link(link)
    sess = server._sessions[link]
    sess.created = time.monotonic() - PRE_WELCOME_TIMEOUT_S - 1

    # Any packet triggers the stale sweep.
    server._on_packet(
        link, proto.encode(proto.make_envelope(proto.T_PING, src=b"\xaa" * 16))
    )
    assert link not in server._sessions
    assert link.torndown


def test_welcomed_sessions_not_reaped():
    server = make_server()
    link = FakeLink(FakeIdentity(b"\xaa" * 16))
    server._on_link(link)
    sess = server._sessions[link]
    sess.welcomed = True
    sess.peer = b"\xaa" * 16
    sess.created = time.monotonic() - PRE_WELCOME_TIMEOUT_S - 1
    server._on_packet(
        link, proto.encode(proto.make_envelope(proto.T_PING, src=b"\xaa" * 16))
    )
    assert link in server._sessions


# --- plugins: wasm bundle path jail -------------------------------------------


def test_wasm_bundle_rejects_traversal_entry(tmp_path):
    from meshchatx.src.backend.plugin_wasm_bundle import (
        WasmBundle,
        validate_embedded_bundle,
        write_wasm_bundle,
    )

    bundle = WasmBundle(
        wasm_binary=b"\x00asm\x01\x00\x00\x00",
        manifest={"id": "x", "backend": {"entry": "../escape.wasm"}},
        files={},
    )
    with pytest.raises(ValueError):
        validate_embedded_bundle(bundle)
    with pytest.raises(ValueError):
        write_wasm_bundle(str(tmp_path / "out"), bundle)

    bundle.manifest["backend"]["entry"] = "C:/windows/evil.wasm"
    with pytest.raises(ValueError):
        validate_embedded_bundle(bundle)

    bundle.manifest["backend"]["entry"] = "/abs/evil.wasm"
    with pytest.raises(ValueError):
        validate_embedded_bundle(bundle)


def test_wasm_bundle_legit_entry_ok(tmp_path):
    from meshchatx.src.backend.plugin_wasm_bundle import (
        WasmBundle,
        validate_embedded_bundle,
        write_wasm_bundle,
    )

    bundle = WasmBundle(
        wasm_binary=b"\x00asm\x01\x00\x00\x00",
        manifest={"id": "x", "backend": {"entry": "backend/plugin.wasm"}},
        files={},
    )
    validate_embedded_bundle(bundle)
    write_wasm_bundle(str(tmp_path / "out"), bundle)
    assert (tmp_path / "out" / "backend" / "plugin.wasm").is_file()


def test_safe_extract_zip_counts_real_bytes(tmp_path):
    from meshchatx.src.backend.plugin_guard import (
        MAX_EXTRACT_BYTES,
        safe_extract_zip,
    )

    # A member that decompresses far beyond its declared size must trip the cap.
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        info = zipfile.ZipInfo("big.bin")
        zf.writestr(info, b"A" * (MAX_EXTRACT_BYTES + 1024))
    zip_path = tmp_path / "plugin.zip"
    zip_path.write_bytes(buf.getvalue())
    with pytest.raises(Exception, match="too large"):
        safe_extract_zip(str(zip_path), str(tmp_path / "out"))


# --- map data: bounded coerce --------------------------------------------------


def test_coerce_map_request_body_bounds_reader():
    from meshchatx.src.backend.map_data_manager import (
        MapDataError,
        coerce_map_request_body,
    )

    class HugeReader:
        def read(self, n=-1):
            return b"x" * (n if n >= 0 else 10 * 1024 * 1024)

    with pytest.raises(MapDataError):
        coerce_map_request_body(HugeReader(), max_bytes=1024)
    assert coerce_map_request_body(b"small", max_bytes=1024) == b"small"


# --- rnx: config sanitation ----------------------------------------------------


def test_rnx_rejects_extra_args_and_escapes(tmp_path):
    from meshchatx.src.backend.rnx_manager import RNXManager

    mgr = RNXManager(str(tmp_path))
    with pytest.raises(ValueError):
        mgr.sanitize_session_config({"extra_args": "--evil"})
    with pytest.raises(ValueError):
        mgr.sanitize_session_config({"config_path": "/etc/passwd"})
    ok = mgr.sanitize_session_config(
        {"config_path": str(tmp_path / "cfg")},
    )
    assert ok["config_path"].endswith("cfg")


# --- shared-instance RPC cannot wedge the event loop ---------------------------


def test_reticulum_rpc_offloads_when_shared_instance():
    import asyncio

    from meshchatx.meshchat import ReticulumMeshChat

    app = ReticulumMeshChat.__new__(ReticulumMeshChat)

    calls = []

    class FakeReticulum:
        is_connected_to_shared_instance = True

        def get_path_table(self):
            calls.append(1)
            return {"a": 1}

    app.reticulum = FakeReticulum()
    out = asyncio.run(app._reticulum_rpc("get_path_table"))
    assert out == {"a": 1}
    assert calls == [1]


def test_reticulum_rpc_inline_when_local():
    import asyncio

    from meshchatx.meshchat import ReticulumMeshChat

    app = ReticulumMeshChat.__new__(ReticulumMeshChat)

    class FakeReticulum:
        is_connected_to_shared_instance = False

        def get_path_table(self):
            return {"b": 2}

    app.reticulum = FakeReticulum()
    assert asyncio.run(app._reticulum_rpc("get_path_table")) == {"b": 2}


def test_interface_stats_rpc_timeout_returns_cached_or_empty(monkeypatch):
    import asyncio
    import time

    import meshchatx.meshchat as meshchat_mod
    from meshchatx.meshchat import ReticulumMeshChat

    app = ReticulumMeshChat.__new__(ReticulumMeshChat)
    monkeypatch.setattr(meshchat_mod, "_INTERFACE_STATS_RPC_TIMEOUT_S", 0.3)
    monkeypatch.setattr(meshchat_mod, "_INTERFACE_STATS_CACHE_S", 0.0)

    def dead_rpc():
        # Short enough that the default-executor join on loop shutdown does
        # not dominate the test, long enough to outlive the 0.3s deadline.
        time.sleep(2)

    class FakeReticulum:
        is_connected_to_shared_instance = True

        def get_interface_stats(self):
            dead_rpc()

    app.reticulum = FakeReticulum()

    t0 = time.monotonic()
    out = asyncio.run(app._aget_interface_stats_payload())
    assert out == {"interfaces": []}
    assert time.monotonic() - t0 < 5


def test_deadlined_rpc_connection_times_out():
    import multiprocessing

    from meshchatx.src.backend.rns_startup_recovery import (
        _DeadlinedRpcConnection,
    )

    a, b = multiprocessing.Pipe()
    conn = _DeadlinedRpcConnection(b, 0.2)
    import pytest as _pytest

    with _pytest.raises(TimeoutError):
        conn.recv_bytes()
    a.send_bytes(b"hello")
    assert conn.poll(0.1)
    assert conn.recv_bytes() == b"hello"
    a.close()
    conn.close()
