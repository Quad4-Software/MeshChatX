# SPDX-License-Identifier: 0BSD

import base64
import json
import os
import sys
import types

import pytest

from meshchatx.src.backend.plugin_guard import PluginSecurityError
from meshchatx.src.backend.plugin_manager import PluginManager

WASM_BYTES = bytes.fromhex(
    "0061736d01000000"
    "010d0260017f017f60037f7f7f017f"
    "0303020001"
    "0503010001"
    "071b0305616c6c6f630000066d656d6f7279020006696e766f6b650001"
    "0a0b02040020000b040041000b"
)
WASM_NO_ALLOC_BYTES = bytes.fromhex(
    "0061736d01000000"
    "01080160037f7f7f017f"
    "03020100"
    "0503010001"
    "071302066d656d6f7279020006696e766f6b650000"
    "0a0601040041000b"
)
WASM_EMPTY_BYTES = b"\x00asm\x01\x00\x00\x00"
PYTHON_MAIN = (
    "def invoke(method, args, host=None):\n"
    "    if method == 'boom':\n"
    "        raise ValueError('python boom')\n"
    "    return {'echo': args.get('value')}\n"
)
MANAGERS_ALL = [
    "status.read",
    "contacts.read",
    "nodes.read",
    "conversations.list",
    "messages.read",
    "message.send",
    "telemetry.read",
    "debugLog.read",
    "destinationPath.read",
    "rnsLink.open",
    "rnsLink.identify",
    "rnsLink.request",
    "rnsLink.send",
    "rnsLink.close",
]


def _make_manager(tmp_path, app=None):
    return PluginManager(str(tmp_path), app=app)


def _manifest(plugin_id="com.example.apis", permissions=None, **extra):
    manifest = {
        "id": plugin_id,
        "version": "1.0.0",
        "apiVersion": 1,
        "name": "API Test",
        "permissions": permissions if permissions is not None else {},
    }
    manifest.update(extra)
    return manifest


def _install(manager, tmp_path, name, manifest, files=None, granted=None):
    source = tmp_path / name
    source.mkdir(parents=True, exist_ok=True)
    (source / "plugin.json").write_text(json.dumps(manifest), encoding="utf-8")
    for rel, content in (files or {}).items():
        path = source / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding="utf-8")
    return manager.install_from_directory(
        str(source),
        granted_permissions=list(granted) if granted is not None else None,
    )["id"]


def _enabled_plugin(manager, tmp_path, name, manifest, files=None, granted=None):
    plugin_id = _install(
        manager, tmp_path, name, manifest, files=files, granted=granted
    )
    manager.enable(plugin_id)
    return plugin_id


def _api_plugin(
    tmp_path, name="apis", plugin_id="com.example.apis", granted=None, **extra
):
    manager = _make_manager(tmp_path)
    manifest = _manifest(
        plugin_id=plugin_id,
        permissions={"managers": MANAGERS_ALL},
        **extra,
    )
    pid = _enabled_plugin(manager, tmp_path, name, manifest, granted=granted)
    return manager, pid


class FakeApp:
    def __init__(self, **attrs):
        self.reticulum = attrs.pop("reticulum", object())
        self.plugins_enabled = attrs.pop("plugins_enabled", True)
        self.broadcasts = []
        for key, value in attrs.items():
            setattr(self, key, value)

    def websocket_broadcast(self, message):
        self.broadcasts.append(message)


class FakeProvider:
    def __init__(self, fail_on=()):
        self.fail_on = set(fail_on)

    def fetchone(self, sql):
        for table in self.fail_on:
            if f"FROM {table}" in sql:
                raise RuntimeError("db gone")
        return {"n": 5}


class FakeContacts:
    def __init__(self, rows=None, total=0):
        self.rows = rows if rows is not None else []
        self.total = total
        self.calls = []

    def get_contacts(self, **kwargs):
        self.calls.append(kwargs)
        return self.rows

    def get_contacts_count(self, **kwargs):
        return self.total


class FakeAnnounces:
    def __init__(self, rows=None):
        self.rows = rows or []

    def get_announces(self, **kwargs):
        return self.rows


class FakeTelemetry:
    def __init__(self, history=None, latest=None):
        self.history = history or []
        self.latest = latest or []
        self.history_calls = []

    def get_telemetry_history(self, destination_hash, **kwargs):
        self.history_calls.append((destination_hash, kwargs))
        return self.history

    def get_all_latest_telemetry(self):
        return self.latest


class FakeMessageHandler:
    def __init__(self, conversations=None, messages=None):
        self.conversations = conversations if conversations is not None else []
        self.messages = messages if messages is not None else []
        self.message_calls = []

    def get_conversations(self, local_hash, **kwargs):
        return self.conversations

    def get_conversation_messages(self, local_hash, peer_hash, **kwargs):
        self.message_calls.append(
            {"local_hash": local_hash, "peer_hash": peer_hash, **kwargs}
        )
        return self.messages


class FakeLinkManager:
    def __init__(self):
        self.open_result = (None, False, "no_route")
        self.identify_result = (True, None)
        self.request_mode = "response"
        self.send_result = (True, None)
        self.close_result = True
        self.open_calls = []
        self.identify_calls = []
        self.request_calls = []
        self.send_calls = []
        self.close_calls = []

    async def open_link(self, dest_hash, aspect, auto_identify=False):
        self.open_calls.append((dest_hash, aspect, auto_identify))
        return self.open_result

    def identify(self, dest_hash, aspect):
        self.identify_calls.append((dest_hash, aspect))
        return self.identify_result

    def request(
        self,
        dest_hash,
        aspect,
        path,
        data,
        response_callback=None,
        failed_callback=None,
        progress_callback=None,
        timeout=None,
    ):
        self.request_calls.append(
            {
                "dest_hash": dest_hash,
                "aspect": aspect,
                "path": path,
                "data": data,
                "timeout": timeout,
            }
        )
        receipt = types.SimpleNamespace(response=b"\x92\xa1a\x01")
        if self.request_mode == "response" and response_callback is not None:
            response_callback(receipt)
        elif self.request_mode == "progress_response":
            if progress_callback is not None:
                progress_callback(receipt)
            if response_callback is not None:
                response_callback(receipt)
        elif self.request_mode == "failed" and failed_callback is not None:
            failed_callback()
        elif self.request_mode == "raise":
            raise RuntimeError("dispatch gone")
        return

    def send_packet(self, dest_hash, aspect, payload):
        self.send_calls.append((dest_hash, aspect, payload))
        return self.send_result

    def close(self, dest_hash, aspect):
        self.close_calls.append((dest_hash, aspect))
        return self.close_result


def _storage_plugin(
    manager, tmp_path, name="stor", granted=("storage:isolated",), permissions=None
):
    manifest = _manifest(
        permissions=permissions if permissions is not None else {"storage": "isolated"},
    )
    return _enabled_plugin(manager, tmp_path, name, manifest, granted=list(granted))


class TestStorage:
    def test_delete_list_clear(self, tmp_path):
        manager = _make_manager(tmp_path)
        pid = _storage_plugin(manager, tmp_path)
        manager.storage_set(pid, "b", "2")
        manager.storage_set(pid, "a", "1")
        manager.storage_set(pid, "c", "3")
        assert manager.storage_delete(pid, "b") is True
        assert manager.storage_delete(pid, "missing") is False
        assert manager.storage_list(pid) == ["a", "c"]
        assert manager.storage_list(pid, limit=1) == ["a"]
        assert manager.storage_list(pid, limit=9999)[-1] == "c"
        assert manager.storage_clear(pid) == 2
        assert manager.storage_list(pid) == []

    def test_denied_without_grant(self, tmp_path):
        manager = _make_manager(tmp_path)
        pid = _enabled_plugin(
            manager,
            tmp_path,
            "stor",
            _manifest(permissions={"storage": "isolated"}),
            granted=[],
        )
        for call in (
            lambda: manager.storage_delete(pid, "k"),
            lambda: manager.storage_list(pid),
            lambda: manager.storage_clear(pid),
        ):
            with pytest.raises(PermissionError):
                call()

    def test_none_mode_denied(self, tmp_path):
        manager = _make_manager(tmp_path)
        pid = _enabled_plugin(
            manager,
            tmp_path,
            "stor",
            _manifest(permissions={"storage": "none"}),
            granted=["storage:none"],
        )
        with pytest.raises(PermissionError):
            manager.storage_list(pid)


class TestNetwork:
    def test_fetch_allowed_and_disabled(self, tmp_path):
        manager = _make_manager(tmp_path)
        pid = _enabled_plugin(
            manager,
            tmp_path,
            "net",
            _manifest(permissions={"network": "fetch"}),
        )
        assert manager.network_fetch_allowed(pid) is True
        manager.disable(pid)
        assert manager.network_fetch_allowed(pid) is False

    def test_none_mode_denied(self, tmp_path):
        manager = _make_manager(tmp_path)
        pid = _enabled_plugin(
            manager,
            tmp_path,
            "net",
            _manifest(permissions={"network": "none"}),
        )
        assert manager.network_fetch_allowed(pid) is False


class TestManagers:
    def test_status_read_counts_and_version(self, tmp_path):
        provider = FakeProvider()
        app = FakeApp(
            database=types.SimpleNamespace(provider=provider), version="4.5.6"
        )
        manager, pid = _api_plugin(tmp_path)
        manager.set_app(app)
        result = manager.call_manager(pid, "status.read", {})
        assert result["ok"] is True
        assert result["version"] == "4.5.6"
        assert result["counts"] == {
            "contacts": 5,
            "announces": 5,
            "lxmf_messages": 5,
            "lxmf_telemetry": 5,
        }
        provider.fail_on.add("announces")
        result = manager.call_manager(pid, "status.read", {})
        assert result["counts"]["announces"] == -1

    def test_status_read_no_database(self, tmp_path):
        manager, pid = _api_plugin(tmp_path)
        manager.set_app(FakeApp())
        result = manager.call_manager(pid, "status.read", {})
        assert result["counts"] == {}
        assert result["version"] == ""

    def test_contacts_read(self, tmp_path):
        rows = [
            {
                "id": 1,
                "name": "Alice",
                "remote_identity_hash": "h",
                "lxmf_address": "a",
                "lxst_address": "l",
                "created_at": "c",
                "updated_at": "u",
                "secret_field": "NO",
            },
            {"id": 2, "name": "Bob"},
            "not-a-dict",
        ]
        contacts = FakeContacts(rows=rows, total=42)
        app = FakeApp(database=types.SimpleNamespace(contacts=contacts))
        manager, pid = _api_plugin(tmp_path)
        manager.set_app(app)
        result = manager.call_manager(
            pid,
            "contacts.read",
            {"search": "al", "limit": 10, "offset": 5},
        )
        assert contacts.calls == [{"search": "al", "limit": 10, "offset": 5}]
        assert result["ok"] is True
        assert result["total"] == 42
        assert result["contacts"] == [
            {
                "id": 1,
                "name": "Alice",
                "remote_identity_hash": "h",
                "lxmf_address": "a",
                "lxst_address": "l",
                "created_at": "c",
                "updated_at": "u",
            },
            {"id": 2, "name": "Bob"},
        ]
        manager.call_manager(pid, "contacts.read", {"offset": "abc"})
        assert contacts.calls[-1]["offset"] == 0
        with pytest.raises(ValueError):
            manager.call_manager(pid, "contacts.read", {"search": 123})
        manager.set_app(FakeApp())
        with pytest.raises(RuntimeError):
            manager.call_manager(pid, "contacts.read", {})

    def test_nodes_read(self, tmp_path):
        rows = [
            {
                "destination_hash": "aa",
                "identity_hash": "ih",
                "aspect": "meshchat",
                "app_data": "ad",
                "timestamp": 1,
                "updated_at": 2,
                "propagation_node_count": 3,
                "extra": "drop",
            },
            "not-a-dict",
        ]
        announces = FakeAnnounces(rows=rows)
        app = FakeApp(database=types.SimpleNamespace(announces=announces))
        manager, pid = _api_plugin(tmp_path)
        manager.set_app(app)
        with pytest.raises(ValueError):
            manager.call_manager(pid, "nodes.read", {"aspect": 5})
        result = manager.call_manager(
            pid, "nodes.read", {"aspect": "meshchat", "offset": "bad"}
        )
        assert result["ok"] is True
        assert result["nodes"] == [
            {
                "destination_hash": "aa",
                "identity_hash": "ih",
                "aspect": "meshchat",
                "app_data": "ad",
                "timestamp": 1,
                "updated_at": 2,
                "propagation_node_count": 3,
            }
        ]
        manager.set_app(FakeApp())
        with pytest.raises(RuntimeError):
            manager.call_manager(pid, "nodes.read", {})

    def test_conversations_list_edges(self, tmp_path):
        handler = FakeMessageHandler(
            conversations=[
                {
                    "peer_hash": "ab" * 32,
                    "state": "delivered",
                    "title": "hi",
                    "content": "SECRET",
                    "extra": "x",
                },
                "not-a-dict",
            ]
        )
        app = FakeApp(
            message_handler=handler,
            local_lxmf_destination=types.SimpleNamespace(hash=b"\x01" * 32),
        )
        manager, pid = _api_plugin(tmp_path)
        manager.set_app(app)
        result = manager.call_manager(
            pid,
            "conversations.list",
            {"search": "x", "limit": 5, "offset": "bad"},
        )
        assert result["ok"] is True
        assert result["conversations"][0] == {
            "peer_hash": "ab" * 32,
            "state": "delivered",
            "title": "hi",
        }
        assert result["conversations"][1] == {}
        with pytest.raises(ValueError):
            manager.call_manager(pid, "conversations.list", {"search": 123})
        manager.set_app(FakeApp())
        with pytest.raises(RuntimeError):
            manager.call_manager(pid, "conversations.list", {})

    def test_messages_read_edges(self, tmp_path):
        handler = FakeMessageHandler(
            messages=[
                {
                    "id": 1,
                    "hash": "msg1",
                    "source_hash": "src",
                    "destination_hash": "dst",
                    "is_incoming": 1,
                    "state": "delivered",
                    "progress": 100,
                    "delivery_attempts": 0,
                    "next_delivery_attempt_at": None,
                    "title": "t",
                    "content": "hello",
                    "fields": "{}",
                    "timestamp": 1,
                    "rssi": -50,
                    "snr": 10,
                    "quality": 90,
                    "is_spam": 0,
                    "created_at": "2024-01-01T00:00:00Z",
                    "updated_at": "2024-01-01T00:00:00Z",
                }
            ]
        )
        app = FakeApp(
            message_handler=handler,
            local_lxmf_destination=types.SimpleNamespace(hash="localhash"),
        )
        manager, pid = _api_plugin(tmp_path)
        manager.set_app(app)
        result = manager.call_manager(
            pid,
            "messages.read",
            {"peer_hash": "cd" * 32, "limit": 5, "offset": "bad"},
        )
        assert result["ok"] is True
        assert result["peer_hash"] == "cd" * 32
        assert handler.message_calls[0]["local_hash"] == "localhash"
        assert handler.message_calls[0]["peer_hash"] == "cd" * 32
        assert handler.message_calls[0]["offset"] == 0
        assert len(result["messages"]) == 1
        manager.set_app(FakeApp())
        with pytest.raises(RuntimeError):
            manager.call_manager(pid, "messages.read", {"peer_hash": "cd" * 32})

    def test_message_send_edges(self, tmp_path):
        no_app_manager = _make_manager(tmp_path / "noapp")
        manifest = _manifest(permissions={"managers": ["message.send"]})
        pid = _install(
            no_app_manager,
            tmp_path,
            "send",
            manifest,
            granted=["managers:message.send"],
        )
        no_app_manager.enable(pid)
        with pytest.raises(RuntimeError):
            no_app_manager.call_manager(
                pid,
                "message.send",
                {"destination_hash": "ab" * 32, "content": "x"},
            )

        async def send_ok(**kwargs):
            return (True, None)

        app = types.SimpleNamespace(
            send_message=send_ok,
            websocket_broadcast=lambda message: None,
            plugins_enabled=True,
        )
        manager, pid2 = _api_plugin(tmp_path / "m2", name="apis2")
        manager.set_app(app)
        result = manager.call_manager(
            pid2,
            "message.send",
            {"destination_hash": "ab" * 32, "content": b"\xffbytes", "title": "T"},
        )
        assert result["ok"] is True
        with pytest.raises(ValueError):
            manager.call_manager(
                pid2,
                "message.send",
                {"destination_hash": "ab" * 32, "content": "x", "title": 123},
            )
        manager.set_app(FakeApp())
        with pytest.raises(RuntimeError):
            manager.call_manager(
                pid2,
                "message.send",
                {"destination_hash": "ab" * 32, "content": "x"},
            )

    def test_telemetry_read(self, tmp_path):
        from RNS.vendor import umsgpack

        packed = umsgpack.packb({"speed": 3})
        telemetry = FakeTelemetry(
            latest=[
                {
                    "destination_hash": "aa" * 32,
                    "data": packed,
                    "physical_link": "{bad json",
                    "timestamp": 1,
                    "updated_at": 2,
                },
                "not-a-dict",
                {"destination_hash": "bb" * 32, "data": b"\x00bad"},
            ]
        )
        app = FakeApp(database=types.SimpleNamespace(telemetry=telemetry))
        manager, pid = _api_plugin(tmp_path)
        manager.set_app(app)
        result = manager.call_manager(pid, "telemetry.read", {})
        assert result["ok"] is True
        assert result["total"] == 3
        first = result["telemetry"][0]
        assert first["destination_hash"] == "aa" * 32
        assert first["physical_link"] is None
        assert result["telemetry"][1] == {}
        assert result["telemetry"][2]["telemetry"] is None
        with pytest.raises(ValueError):
            manager.call_manager(pid, "telemetry.read", {"destination_hash": 123})
        with pytest.raises(ValueError):
            manager.call_manager(pid, "telemetry.read", {"limit": "abc"})
        result = manager.call_manager(
            pid,
            "telemetry.read",
            {"destination_hash": "cc" * 32, "offset": "bad"},
        )
        assert telemetry.history_calls[-1][1]["offset"] == 0
        manager.set_app(FakeApp())
        with pytest.raises(RuntimeError):
            manager.call_manager(pid, "telemetry.read", {})

    def test_debug_log_read_branches(self, tmp_path):
        import meshchatx.src.backend.persistent_log_handler as plh

        class FakeMemHandler:
            def get_logs(self, **kwargs):
                return [
                    {"message": "hello", "token": "abc"},
                    "plain",
                    {"message": 123, "extra": 1},
                ]

            def get_total_count(self, **kwargs):
                return 3

        original = plh.memory_log_handler
        plh.memory_log_handler = FakeMemHandler()
        try:
            manager, pid = _api_plugin(tmp_path)
            manager.set_app(FakeApp())
            result = manager.call_manager(
                pid, "debugLog.read", {"limit": -5, "level": None}
            )
            assert result["limit"] == 1
            assert result["total"] == 3
            assert result["logs"][0] == {"message": "hello", "token": "abc"}
            assert result["logs"][1] == "plain"
            assert result["logs"][2] == {"message": 123, "extra": 1}
            result = manager.call_manager(pid, "debugLog.read", {"limit": 9999})
            assert result["limit"] == 500
        finally:
            plh.memory_log_handler = original

        class FakeDbHandler:
            def __init__(self):
                self.calls = []

            def get_logs(self, **kwargs):
                self.calls.append(kwargs)
                return [{"message": "db"}]

            def get_total_count(self, **kwargs):
                return 1

        db_handler = FakeDbHandler()
        plh.memory_log_handler = None
        try:
            app = FakeApp(database=types.SimpleNamespace(debug_logs=db_handler))
            manager2, pid2 = _api_plugin(tmp_path / "m2")
            manager2.set_app(app)
            result = manager2.call_manager(
                pid2,
                "debugLog.read",
                {"search": "x", "level": "warn"},
            )
            assert db_handler.calls[0]["search"] == "x"
            assert db_handler.calls[0]["level"] == "warn"
            assert result["logs"] == [{"message": "db"}]
            manager2.set_app(FakeApp())
            result = manager2.call_manager(pid2, "debugLog.read", {})
            assert result == {"logs": [], "total": 0, "limit": 200}
        finally:
            plh.memory_log_handler = original


class TestDestinationPath:
    def _plugin(self, tmp_path, app):
        manager = _make_manager(tmp_path, app=app)
        manifest = _manifest(permissions={"managers": ["destinationPath.read"]})
        pid = _enabled_plugin(
            manager, tmp_path, "dp", manifest, granted=["managers:destinationPath.read"]
        )
        return manager, pid

    def test_rnpath_handler(self, tmp_path):
        handler = types.SimpleNamespace(
            get_path_table=lambda **kwargs: {
                "table": [
                    {
                        "hash": "aa",
                        "hops": 3,
                        "via": "iface",
                        "interface": "intf",
                        "state": "ok",
                        "timestamp": 1,
                    }
                ],
                "total": 9,
                "responsive": 7,
                "unresponsive": 2,
            }
        )
        manager, pid = self._plugin(tmp_path, FakeApp(rnpath_handler=handler))
        result = manager.call_manager(
            pid, "destinationPath.read", {"search": "a", "limit": "bad"}
        )
        assert result["total"] == 9
        assert result["responsive"] == 7
        assert result["unresponsive"] == 2
        assert result["paths"][0]["destination_hash"] == "aa"
        assert result["paths"][0]["hops"] == 3
        assert result["paths"][0]["via"] == "iface"

    def test_fallback_transport(self, tmp_path):
        reticulum = types.SimpleNamespace(
            get_path_table=lambda: (_ for _ in ()).throw(RuntimeError("gone")),
        )
        manager, pid = self._plugin(tmp_path, FakeApp(reticulum=reticulum))
        result = manager.call_manager(pid, "destinationPath.read", {})
        assert result == {"paths": [], "total": 0, "responsive": 0, "unresponsive": 0}
        result = manager.call_manager(
            pid, "destinationPath.read", {"destination_hash": "zz"}
        )
        assert result["paths"] == [{"destination_hash": "zz", "hops": None}]
        result = manager.call_manager(
            pid, "destinationPath.read", {"destination_hash": "ab" * 32}
        )
        assert result["paths"][0]["destination_hash"] == "ab" * 32
        assert "hops" in result["paths"][0]

    def test_no_reticulum(self, tmp_path):
        manager, pid = self._plugin(tmp_path, FakeApp(reticulum=None))
        result = manager.call_manager(pid, "destinationPath.read", {})
        assert result == {"paths": [], "total": 0, "responsive": 0, "unresponsive": 0}


class TestRnsLink:
    def _plugin(self, tmp_path, app, name="link", managers=None, granted=None):
        manager = _make_manager(tmp_path, app=app)
        manifest = _manifest(
            permissions={"managers": managers or ["rnsLink.request"]},
        )
        pid = _enabled_plugin(
            manager,
            tmp_path,
            name,
            manifest,
            granted=granted or ["managers:rnsLink.request"],
        )
        return manager, pid

    def test_no_app(self, tmp_path):
        manager = _make_manager(tmp_path / "noapp")
        manifest = _manifest(permissions={"managers": ["rnsLink.request"]})
        pid = _enabled_plugin(
            manager, tmp_path, "lnk", manifest, granted=["managers:rnsLink.request"]
        )
        with pytest.raises(RuntimeError):
            manager.call_manager(
                pid,
                "rnsLink.request",
                {"destination_hash": "ab" * 32, "aspect": "a", "path": "/p"},
            )

    def test_no_link_manager(self, tmp_path):
        manager, pid = self._plugin(tmp_path, FakeApp())
        with pytest.raises(RuntimeError):
            manager.call_manager(
                pid,
                "rnsLink.request",
                {"destination_hash": "ab" * 32, "aspect": "a", "path": "/p"},
            )

    def test_parse_args(self, tmp_path):
        lm = FakeLinkManager()
        lm.open_result = (object(), True, None)
        manager, pid = self._plugin(tmp_path, FakeApp(rns_link_manager=lm))
        base = {"destination_hash": "ab" * 32, "aspect": "a", "path": "/p"}
        with pytest.raises(ValueError):
            manager.call_manager(pid, "rnsLink.request", {})
        with pytest.raises(ValueError):
            manager.call_manager(
                pid, "rnsLink.request", {"destination_hash": "ab" * 32, "aspect": "a"}
            )
        with pytest.raises(ValueError):
            manager.call_manager(
                pid,
                "rnsLink.request",
                {"destination_hash": "zz", "aspect": "a", "path": "/p"},
            )
        with pytest.raises(ValueError):
            manager.call_manager(
                pid,
                "rnsLink.request",
                {**base, "data_b64": "!!!"},
            )
        with pytest.raises(ValueError):
            manager.call_manager(
                pid,
                "rnsLink.request",
                {**base, "data_b64": base64.b64encode(b"\xc1\xff").decode()},
            )

    def test_request_no_route(self, tmp_path):
        lm = FakeLinkManager()
        manager, pid = self._plugin(tmp_path, FakeApp(rns_link_manager=lm))
        result = manager.call_manager(
            pid,
            "rnsLink.request",
            {"destination_hash": "ab" * 32, "aspect": "test.aspect", "path": "/req"},
        )
        assert result["ok"] is False
        assert result["failure_reason"] == "no_route"
        assert lm.open_calls
        assert lm.request_calls == []

    def test_request_response(self, tmp_path):
        lm = FakeLinkManager()
        lm.open_result = (object(), True, None)
        manager, pid = self._plugin(tmp_path, FakeApp(rns_link_manager=lm))
        from RNS.vendor import umsgpack

        payload = base64.b64encode(umsgpack.packb({"a": 1})).decode()
        result = manager.call_manager(
            pid,
            "rnsLink.request",
            {
                "destination_hash": "ab" * 32,
                "aspect": "test.aspect",
                "path": "/req",
                "data_b64": payload,
                "timeout": "5",
            },
        )
        assert result["ok"] is True
        assert result["body_b64"]
        assert lm.request_calls[0]["data"] == {"a": 1}
        assert lm.request_calls[0]["path"] == "/req"
        assert lm.request_calls[0]["timeout"] == 5.0

    def test_request_modes(self, tmp_path):
        lm = FakeLinkManager()
        lm.open_result = (object(), True, None)
        manager, pid = self._plugin(tmp_path, FakeApp(rns_link_manager=lm))
        args = {"destination_hash": "ab" * 32, "aspect": "test.aspect", "path": "/req"}
        lm.request_mode = "progress_response"
        result = manager.call_manager(pid, "rnsLink.request", args)
        assert result["ok"] is True
        lm.request_mode = "failed"
        result = manager.call_manager(pid, "rnsLink.request", args)
        assert result["ok"] is False
        assert result["failure_reason"] == "request_failed"
        lm.request_mode = "raise"
        result = manager.call_manager(pid, "rnsLink.request", args)
        assert result["ok"] is False
        assert result["failure_reason"].startswith("request_dispatch_failed")

    def test_send_close_identify_open(self, tmp_path):
        lm = FakeLinkManager()
        lm.send_result = (True, None)
        lm.close_result = False
        lm.identify_result = (False, "no_identify")
        lm.open_result = (object(), True, None)
        managers = [
            "rnsLink.send",
            "rnsLink.close",
            "rnsLink.identify",
            "rnsLink.open",
        ]
        manager, pid = self._plugin(
            tmp_path,
            FakeApp(rns_link_manager=lm),
            managers=managers,
            granted=[f"managers:{m}" for m in managers],
        )
        base = {"destination_hash": "ab" * 32, "aspect": "test.aspect"}
        result = manager.call_manager(
            pid,
            "rnsLink.send",
            {**base, "payload_b64": base64.b64encode(b"hi").decode()},
        )
        assert result["ok"] is True
        assert lm.send_calls[0][2] == b"hi"
        with pytest.raises(ValueError):
            manager.call_manager(pid, "rnsLink.send", {**base, "payload_b64": "!!!"})
        result = manager.call_manager(pid, "rnsLink.close", base)
        assert result["ok"] is False
        assert result["failure_reason"] == "no_active_link"
        result = manager.call_manager(pid, "rnsLink.identify", base)
        assert result["ok"] is False
        assert result["failure_reason"] == "no_identify"
        result = manager.call_manager(
            pid, "rnsLink.open", {**base, "auto_identify": True}
        )
        assert result["ok"] is True
        assert result["identified"] is True
        assert lm.open_calls[0][2] is True


class TestInvoke:
    def test_dispatch_and_errors(self, tmp_path):
        manager, pid = _api_plugin(tmp_path)
        manager.disable(pid)
        with pytest.raises(PermissionError):
            manager.invoke(pid, "callManager", {"capability": "status.read"})
        manager.enable(pid)
        result = manager.invoke(
            pid, "callManager", {"capability": "status.read", "args": {}}
        )
        assert result["ok"] is True
        result = manager.invoke(pid, "readPaths", {"destination_hash": "zz"})
        assert result["paths"] == []
        manifestless = _enabled_plugin(
            manager,
            tmp_path,
            "plain",
            _manifest(plugin_id="com.example.plain"),
            granted=[],
        )
        with pytest.raises(ValueError):
            manager.invoke(manifestless, "bogus.method", {})
        with pytest.raises(ValueError):
            manager.invoke(pid, "callManager", {})

    def test_python_invoke_and_grant_revoked(self, tmp_path):
        manager = _make_manager(tmp_path)
        manifest = _manifest(
            plugin_id="com.example.py",
            permissions={"storage": "isolated", "hooks": ["announce.received"]},
            backend={"entry": "backend/main.py", "type": "python"},
        )
        pid = _enabled_plugin(
            manager,
            tmp_path,
            "py",
            manifest,
            files={"backend/main.py": PYTHON_MAIN},
            granted=["backend:python", "storage:isolated", "hooks:announce.received"],
        )
        result = manager.invoke(pid, "echo", {"value": 7})
        assert result["echo"] == 7
        with pytest.raises(ValueError):
            manager.invoke(pid, "boom", {})
        assert manager._plugins[pid].error_count == 1
        record = manager._plugins[pid]
        record.granted_permissions = [
            g for g in record.granted_permissions if g != "backend:python"
        ]
        with pytest.raises(PermissionError):
            manager.invoke(pid, "echo", {})

    def test_wasm_invoke_real_module(self, tmp_path):
        manager = _make_manager(tmp_path)
        manifest = _manifest(
            plugin_id="com.example.wasm",
            permissions={"managers": ["status.read"]},
            backend={"entry": "backend/plugin.wasm", "type": "wasm"},
        )
        pid = _enabled_plugin(
            manager,
            tmp_path,
            "wasm",
            manifest,
            files={"backend/plugin.wasm": WASM_BYTES},
            granted=["managers:status.read"],
        )
        result = manager.invoke(pid, "any.method", {"x": 1})
        assert result == {"ok": True, "logs": []}

    def test_wasm_missing_file_uses_stub(self, tmp_path):
        manager = _make_manager(tmp_path)
        manifest = _manifest(
            plugin_id="com.example.wasm2",
            permissions={"managers": ["status.read"]},
            backend={"entry": "backend/missing.wasm", "type": "wasm"},
        )
        pid = _enabled_plugin(
            manager,
            tmp_path,
            "wasm2",
            manifest,
            granted=["managers:status.read"],
        )
        result = manager.invoke(pid, "m", {})
        assert result["ok"] is True

    def test_wasm_invalid_magic_falls_back(self, tmp_path):
        manager = _make_manager(tmp_path)
        manifest = _manifest(
            plugin_id="com.example.wasm3",
            permissions={"managers": ["status.read"]},
            backend={"entry": "backend/plugin.wasm", "type": "wasm"},
        )
        pid = _enabled_plugin(
            manager,
            tmp_path,
            "wasm3",
            manifest,
            files={"backend/plugin.wasm": b"not-a-wasm-file"},
            granted=["managers:status.read"],
        )
        result = manager.invoke(pid, "m", {})
        assert result["ok"] is True

    def test_wasm_no_alloc_fails(self, tmp_path):
        manager = _make_manager(tmp_path)
        manifest = _manifest(
            plugin_id="com.example.wasm4",
            permissions={"managers": ["status.read"]},
            backend={"entry": "backend/plugin.wasm", "type": "wasm"},
        )
        pid = _enabled_plugin(
            manager,
            tmp_path,
            "wasm4",
            manifest,
            files={"backend/plugin.wasm": WASM_NO_ALLOC_BYTES},
            granted=["managers:status.read"],
        )
        with pytest.raises(PluginSecurityError):
            manager.invoke(pid, "m", {})
        assert manager._plugins[pid].error_count == 1

    def test_wasm_empty_module_fails(self, tmp_path):
        manager = _make_manager(tmp_path)
        manifest = _manifest(
            plugin_id="com.example.wasm5",
            permissions={"managers": ["status.read"]},
            backend={"entry": "backend/plugin.wasm", "type": "wasm"},
        )
        pid = _enabled_plugin(
            manager,
            tmp_path,
            "wasm5",
            manifest,
            files={"backend/plugin.wasm": WASM_EMPTY_BYTES},
            granted=["managers:status.read"],
        )
        with pytest.raises(KeyError):
            manager.invoke(pid, "m", {})
        assert manager._plugins[pid].error_count == 1


class TestHooks:
    def _hook_plugin(
        self, tmp_path, name="hook", backend=None, granted=None, files=None
    ):
        manager = _make_manager(tmp_path, app=FakeApp())
        manifest = _manifest(
            plugin_id=f"com.example.{name}",
            permissions={"hooks": ["announce.received"]},
            **({"backend": backend} if backend else {}),
        )
        pid = _enabled_plugin(
            manager,
            tmp_path,
            name,
            manifest,
            files=files if files is not None else {"backend/plugin.wasm": WASM_BYTES},
            granted=granted or ["hooks:announce.received"],
        )
        return manager, pid

    def test_dispatch_disabled_and_unknown(self, tmp_path):
        manager, pid = self._hook_plugin(tmp_path)
        manager.dispatch_hook("no.such", "announce.received", {})
        record = manager._plugins[pid]
        record.enabled = False
        manager.dispatch_hook(pid, "announce.received", {})
        assert manager._plugins[pid].error_count == 0

    def test_dispatch_tampered_and_hook_denied(self, tmp_path):
        manager, pid = self._hook_plugin(tmp_path)
        record = manager._plugins[pid]
        record.tampered = True
        manager.dispatch_hook(pid, "announce.received", {})
        record.tampered = False
        record.granted_permissions = []
        manager.dispatch_hook(pid, "announce.received", {})
        assert manager._plugins[pid].error_count == 0
        record.granted_permissions = ["hooks:announce.received"]
        manager.dispatch_hook(pid, "announce.received", {"x": 1})
        assert manager.app.broadcasts

    def test_dispatch_plugins_disabled(self, tmp_path):
        app = FakeApp()
        manager = _make_manager(tmp_path, app=app)
        manifest = _manifest(permissions={"hooks": ["announce.received"]})
        pid = _enabled_plugin(
            manager, tmp_path, "hk", manifest, granted=["hooks:announce.received"]
        )
        app.plugins_enabled = False
        manager.dispatch_hook(pid, "announce.received", {"x": 1})
        assert app.broadcasts == []

    def test_dispatch_wasm_hook_broadcasts(self, tmp_path):
        manager, pid = self._hook_plugin(
            tmp_path,
            backend={"entry": "backend/plugin.wasm", "type": "wasm"},
            granted=["hooks:announce.received"],
        )
        manager.dispatch_hook(pid, "announce.received", {"aspect": "x"})
        assert manager.app.broadcasts
        payload = json.loads(manager.app.broadcasts[0])
        assert payload["type"] == "plugin.event"
        assert payload["plugin_id"] == pid
        assert payload["event"] == "announce.received"
        assert payload["payload"] == {"aspect": "x"}

    def test_dispatch_python_no_grant_returns(self, tmp_path):
        manager, pid = self._hook_plugin(
            tmp_path,
            name="pyhook",
            backend={"entry": "backend/main.py", "type": "python"},
            granted=["backend:python", "hooks:announce.received"],
            files={"backend/main.py": PYTHON_MAIN},
        )
        record = manager._plugins[pid]
        record.granted_permissions = [
            g for g in record.granted_permissions if g != "backend:python"
        ]
        manager.dispatch_hook(pid, "announce.received", {})
        assert manager._plugins[pid].error_count == 0
        assert manager.app.broadcasts == []

    def test_dispatch_exception_records_failure(self, tmp_path):
        manager, pid = self._hook_plugin(
            tmp_path,
            name="badwasm",
            backend={"entry": "backend/plugin.wasm", "type": "wasm"},
            granted=["hooks:announce.received"],
            files={"backend/plugin.wasm": WASM_EMPTY_BYTES},
        )
        manager.dispatch_hook(pid, "announce.received", {})
        assert manager._plugins[pid].error_count == 1

    def test_on_announce_received(self, tmp_path):
        manager, _pid = self._hook_plugin(tmp_path)
        captured = []
        manager.dispatch_hook = lambda plugin_id, hook, payload: captured.append(
            (plugin_id, hook, payload)
        )
        manager.on_announce_received(
            "aspect.test",
            b"\x01" * 32,
            announced_identity=b"ident",
            app_data=b"appdata",
            announce_packet_hash=b"\x02" * 32,
        )
        assert captured[0][2] == {
            "aspect": "aspect.test",
            "destination_hash": "01" * 32,
            "app_data": "appdata",
            "announce_packet_hash": "02" * 32,
        }
        manager.on_announce_received(
            "aspect2",
            "strhash",
            announced_identity="ident2",
            app_data="strdata",
            announce_packet_hash="strph",
        )
        assert captured[1][2]["destination_hash"] == "strhash"
        assert captured[1][2]["app_data"] == "strdata"
        assert captured[1][2]["announce_packet_hash"] == "strph"

    def test_on_rns_link_event(self, tmp_path):
        manager = _make_manager(tmp_path, app=FakeApp())
        manifest = _manifest(permissions={"hooks": ["rns.link.event"]})
        _enabled_plugin(
            manager, tmp_path, "rl", manifest, granted=["hooks:rns.link.event"]
        )
        manager.on_rns_link_event(
            {
                "event": "link.up",
                "destination_hash": "ab" * 32,
                "aspect": "a",
                "payload_b64": "eA==",
            }
        )
        assert manager.app.broadcasts
        payload = json.loads(manager.app.broadcasts[0])
        assert payload["event"] == "rns.link.event"
        assert payload["payload"]["event"] == "link.up"

    def test_restore_and_unregister_hooks(self, tmp_path, monkeypatch):
        import RNS

        import meshchatx.src.backend.announce_handler as ah

        registered = []
        deregistered = []
        monkeypatch.setattr(
            RNS.Transport,
            "register_announce_handler",
            classmethod(lambda cls, handler: registered.append(handler)),
        )
        monkeypatch.setattr(
            RNS.Transport,
            "deregister_announce_handler",
            classmethod(lambda cls, handler: deregistered.append(handler)),
        )
        monkeypatch.setattr(ah, "AnnounceHandler", lambda *args, **kwargs: object())

        app = FakeApp()
        manager = _make_manager(tmp_path, app=app)
        manifest = _manifest(
            permissions={"hooks": ["announce.received"]},
            backend={"entry": "backend/plugin.wasm", "type": "wasm"},
        )
        pid1 = _enabled_plugin(
            manager,
            tmp_path,
            "hk1",
            manifest,
            files={"backend/plugin.wasm": WASM_BYTES},
            granted=["hooks:announce.received"],
        )
        pid2 = _enabled_plugin(
            manager,
            tmp_path,
            "hk2",
            _manifest(
                plugin_id="com.example.hk2",
                permissions={"hooks": ["announce.received"]},
            ),
            granted=["hooks:announce.received"],
        )
        manager.restore_enabled_hooks()
        assert len(registered) == 1
        assert app._plugin_announce_handler_registered is True

        original_register = manager._register_plugin_hooks
        manager._register_plugin_hooks = lambda record: (_ for _ in ()).throw(
            RuntimeError("reg fail")
        )
        manager.restore_enabled_hooks()
        manager._register_plugin_hooks = original_register

        manager.disable(pid2)
        assert deregistered == []
        manager.disable(pid1)
        assert deregistered
        assert app._plugin_announce_handler is None
        assert app._plugin_announce_handler_registered is False

    def test_unregister_no_handler_and_error(self, tmp_path, monkeypatch):
        import RNS

        manager, pid = self._hook_plugin(tmp_path)
        app = manager.app
        manager.disable(pid)
        record = manager._plugins[pid]
        handler_obj = object()
        app._plugin_announce_handler = handler_obj
        app._plugin_announce_handler_registered = True
        monkeypatch.setattr(
            RNS.Transport,
            "deregister_announce_handler",
            classmethod(
                lambda cls, handler: (_ for _ in ()).throw(RuntimeError("boom"))
            ),
        )
        manager._unregister_plugin_hooks(record)
        assert app._plugin_announce_handler is handler_obj


class TestRuntimeValidation:
    def test_frontend_validation(self, tmp_path):
        manager = _make_manager(tmp_path)
        manifest = _manifest(frontend={"entry": ""})
        source = tmp_path / "fe"
        source.mkdir()
        (source / "plugin.json").write_text(json.dumps(manifest))
        (source / "index.html").write_text("x")
        pid = manager.install_from_directory(str(source))["id"]
        with pytest.raises(ValueError):
            manager.enable(pid)

        manifest2 = _manifest(
            plugin_id="com.example.fe2", frontend={"entry": "index.html"}
        )
        source2 = tmp_path / "fe2"
        source2.mkdir()
        (source2 / "plugin.json").write_text(json.dumps(manifest2))
        (source2 / "index.html").write_text("")
        pid2 = manager.install_from_directory(str(source2))["id"]
        with pytest.raises(ValueError):
            manager.enable(pid2)

    def test_backend_entry_missing(self, tmp_path):
        manager = _make_manager(tmp_path)
        manifest = _manifest(
            plugin_id="com.example.be",
            backend={"entry": "backend/plugin.wasm", "type": "wasm"},
        )
        pid = _install(
            manager,
            tmp_path,
            "be",
            manifest,
            files={"backend/plugin.wasm": WASM_BYTES},
            granted=[],
        )
        record = manager._plugins[pid]
        record.manifest["backend"] = {"type": "wasm"}
        with pytest.raises(ValueError):
            manager._validate_plugin_runtime(record)

    def test_python_no_grant_and_empty(self, tmp_path):
        manager = _make_manager(tmp_path)
        manifest = _manifest(
            plugin_id="com.example.py3",
            backend={"entry": "backend/main.py", "type": "python"},
        )
        pid = _install(
            manager,
            tmp_path,
            "py3",
            manifest,
            files={"backend/main.py": PYTHON_MAIN},
            granted=[],
        )
        with pytest.raises(PermissionError):
            manager.enable(pid)

        manifest2 = _manifest(
            plugin_id="com.example.py4",
            backend={"entry": "backend/main.py", "type": "python"},
        )
        pid2 = _install(
            manager,
            tmp_path,
            "py4",
            manifest2,
            files={"backend/main.py": ""},
            granted=["backend:python"],
        )
        with pytest.raises(ValueError):
            manager.enable(pid2)

    def test_wasm_invalid_module(self, tmp_path):
        manager = _make_manager(tmp_path)
        manifest = _manifest(
            plugin_id="com.example.wasm6",
            backend={"entry": "backend/plugin.wasm", "type": "wasm"},
        )
        pid = _install(
            manager,
            tmp_path,
            "wasm6",
            manifest,
            files={"backend/plugin.wasm": b"\x00asm\xff\xff\xff\xff"},
            granted=[],
        )
        with pytest.raises(ValueError):
            manager.enable(pid)

    def test_python_activate_failure_rolls_back(self, tmp_path):
        manager = _make_manager(tmp_path)
        manifest = _manifest(
            plugin_id="com.example.py5",
            backend={"entry": "backend/main.py", "type": "python"},
        )
        pid = _install(
            manager,
            tmp_path,
            "py5",
            manifest,
            files={"backend/main.py": "def broken(:\n"},
            granted=["backend:python"],
        )
        with pytest.raises(SyntaxError):
            manager.enable(pid)
        record = manager._plugins[pid]
        assert record.enabled is False


class TestIntegrity:
    def test_require_untampered_branches(self, tmp_path):
        manager = _make_manager(tmp_path)
        manifest = _manifest(plugin_id="com.example.int")
        pid = _install(manager, tmp_path, "int", manifest, granted=[])
        record = manager._plugins[pid]
        record.integrity_hash = None
        manager._require_untampered_backend(record)
        assert record.integrity_hash
        with open(os.path.join(record.install_path, "plugin.json"), "w") as handle:
            handle.write('{"tampered": true}')
        with pytest.raises(PluginSecurityError):
            manager._require_untampered_backend(record)
        assert record.tampered is True
        record.tampered = True
        with pytest.raises(PluginSecurityError):
            manager._require_untampered_backend(record)

    def test_verify_integrity_on_load(self, tmp_path):
        manager = _make_manager(tmp_path)
        manifest = _manifest(plugin_id="com.example.int2")
        pid = _install(manager, tmp_path, "int2", manifest, granted=[])
        record = manager._plugins[pid]
        record.integrity_hash = None
        assert manager._verify_integrity_on_load(record) is True
        assert record.integrity_hash
        with open(os.path.join(record.install_path, "plugin.json"), "w") as handle:
            handle.write('{"bad": 1}')
        record.tampered = False
        assert manager._verify_integrity_on_load(record) is True
        assert record.tampered is True

    def test_enable_refuses_tampered(self, tmp_path):
        manager = _make_manager(tmp_path)
        manifest = _manifest(plugin_id="com.example.int3")
        pid = _install(manager, tmp_path, "int3", manifest, granted=[])
        record = manager._plugins[pid]
        with open(os.path.join(record.install_path, "plugin.json"), "w") as handle:
            handle.write('{"bad": 1}')
        record.integrity_hash = "stale"
        with pytest.raises(PluginSecurityError):
            manager.enable(pid)
        assert record.enabled is False


class TestPluginRecordHelpers:
    def test_backend_type_and_entry_path(self, tmp_path):
        manager = _make_manager(tmp_path)
        manifest = _manifest(
            plugin_id="com.example.rec",
            backend={"entry": "backend/main.py", "type": "python"},
        )
        pid = _install(
            manager,
            tmp_path,
            "rec",
            manifest,
            files={"backend/main.py": PYTHON_MAIN},
            granted=["backend:python"],
        )
        record = manager._plugins[pid]
        assert manager._backend_type(record) == "python"
        assert os.path.basename(manager._python_entry_path(record)) == "main.py"
        record.manifest.pop("backend")
        assert manager._backend_type(record) is None
        record.manifest["backend"] = {}
        assert manager._backend_type(record) is None
        record.manifest["backend"] = {"type": "wasm"}
        assert manager._backend_type(record) == "wasm"
        record.manifest["backend"] = {"entry": "", "type": "python"}
        with pytest.raises(ValueError):
            manager._python_entry_path(record)
        record.manifest["backend"] = {"entry": "missing.py", "type": "python"}
        with pytest.raises(ValueError):
            manager._python_entry_path(record)
        record.manifest["backend"] = {"entry": "../escape.py", "type": "python"}
        with pytest.raises(PluginSecurityError):
            manager._python_entry_path(record)


class TestManifestValidation:
    @pytest.mark.parametrize(
        "manifest",
        [
            "not-a-dict",
            {"version": "1", "apiVersion": 1},
            {"id": "x", "apiVersion": 1},
            {"id": "x", "version": "1"},
            {"id": "x", "version": "1", "apiVersion": "x"},
            {"id": "x", "version": "1", "apiVersion": 2},
            {"id": "x", "version": "1", "apiVersion": 1, "backend": "wasm"},
            {"id": "x", "version": "1", "apiVersion": 1, "backend": {}},
            {"id": "x", "version": "1", "apiVersion": 1, "backend": {"entry": ""}},
            {
                "id": "x",
                "version": "1",
                "apiVersion": 1,
                "backend": {"entry": "a.wasm", "type": "rust"},
            },
            {
                "id": "x",
                "version": "1",
                "apiVersion": 1,
                "backend": {"entry": "main.txt", "type": "python"},
            },
            {
                "id": "x",
                "version": "1",
                "apiVersion": 1,
                "backend": {"entry": "../escape.py", "type": "python"},
            },
            {
                "id": "x",
                "version": "1",
                "apiVersion": 1,
                "permissions": {"managers": ["bogus.cap"]},
            },
            {
                "id": "x",
                "version": "1",
                "apiVersion": 1,
                "permissions": {"hooks": ["bogus.hook"]},
            },
            {"id": "x", "version": "1", "apiVersion": 1, "permissions": "bad"},
        ],
    )
    def test_invalid_manifests(self, tmp_path, manifest):
        manager = _make_manager(tmp_path)
        with pytest.raises(ValueError):
            manager._validate_manifest(manifest)


class TestMisc:
    def test_asset_path_symlink_escape(self, tmp_path):
        manager = _make_manager(tmp_path)
        manifest = _manifest(plugin_id="com.example.asset")
        pid = _enabled_plugin(manager, tmp_path, "asset", manifest, granted=[])
        record = manager._plugins[pid]
        outside = tmp_path / "outside"
        outside.mkdir()
        (outside / "secret.txt").write_text("x")
        os.symlink(str(outside), os.path.join(record.install_path, "link"))
        with pytest.raises(PluginSecurityError):
            manager.asset_path(pid, "link/secret.txt")

    def test_locale_path_non_str_directory(self, tmp_path):
        manager = _make_manager(tmp_path)
        manifest = _manifest(plugin_id="com.example.loc")
        pid = _install(manager, tmp_path, "loc", manifest, granted=[])
        record = manager._plugins[pid]
        record.manifest["i18n"] = {"directory": 123}
        assert manager.locale_path(pid, "en") is None

    def test_report_failure(self, tmp_path):
        manager = _make_manager(tmp_path)
        assert manager.report_failure("no.such.plugin", "why", "test") is None
        manifest = _manifest(plugin_id="com.example.rep")
        pid = _install(manager, tmp_path, "rep", manifest, granted=[])
        manager.report_failure(pid, "why", "test")
        assert manager._plugins[pid].error_count == 1

    def test_trusted_publishers(self, tmp_path):
        manager = _make_manager(tmp_path)
        assert manager.list_trusted_publishers() == []
        identity = "ab" * 32
        manager.add_trusted_publisher(identity, "Test Publisher")
        assert manager.list_trusted_publishers()
        assert manager.trusted_publishers_tampered()[0] is False
        manager.remove_trusted_publisher(identity)
        assert manager.list_trusted_publishers() == []

    def test_remove_plugin(self, tmp_path):
        manager = _make_manager(tmp_path)
        manifest = _manifest(
            plugin_id="com.example.rm",
            permissions={"storage": "isolated"},
        )
        pid = _enabled_plugin(
            manager, tmp_path, "rm", manifest, granted=["storage:isolated"]
        )
        manager.storage_set(pid, "k", "v")
        manager.remove(pid)
        assert pid not in manager._plugins
        with pytest.raises(KeyError):
            manager.remove(pid)

    def test_install_from_directory_missing_manifest(self, tmp_path):
        manager = _make_manager(tmp_path)
        empty = tmp_path / "empty"
        empty.mkdir()
        with pytest.raises(ValueError):
            manager.install_from_directory(str(empty))

    def test_preview_missing_manifest(self, tmp_path):
        manager = _make_manager(tmp_path)
        empty = tmp_path / "empty2"
        empty.mkdir()
        with pytest.raises(ValueError):
            manager._build_preview_from_directory(str(empty))
        with pytest.raises(PluginSecurityError):
            manager.preview_from_zip_bytes(b"not a zip")

    def test_wasm_bytes_size_limits(self, tmp_path):
        manager = _make_manager(tmp_path)
        big = b"\x00asm" + b"x" * (33 * 1024 * 1024)
        with pytest.raises(PluginSecurityError):
            manager.preview_from_wasm_bytes(big)
        with pytest.raises(PluginSecurityError):
            manager.install_from_wasm_bytes(big)

    def test_wasmtime_import_error_and_cache(self, tmp_path, monkeypatch):
        manager = _make_manager(tmp_path)
        monkeypatch.setitem(sys.modules, "wasmtime", None)
        with pytest.raises(RuntimeError, match="wasmtime is required"):
            manager._load_wasmtime()
        manager2 = _make_manager(tmp_path / "m2")
        sentinel = object()
        manager2._wasmtime = sentinel
        assert manager2._load_wasmtime() is sentinel

    def test_misc_utils(self, tmp_path):
        manager = _make_manager(tmp_path)
        manager.set_app(FakeApp())
        PluginManager._chmod_path(str(tmp_path / "missing" / "file"), 0o777)
        tree = tmp_path / "tree"
        (tree / "__pycache__").mkdir(parents=True)
        (tree / "__pycache__" / "m.pyc").write_bytes(b"x")
        (tree / "mod.pyc").write_bytes(b"y")
        (tree / "mod.py").write_text("z")
        PluginManager._strip_install_tree_bytecode(str(tree))
        assert not (tree / "__pycache__").exists()
        assert not (tree / "mod.pyc").exists()
        assert (tree / "mod.py").exists()
        manager._remove_install_tree(str(tmp_path / "missing-tree"))
        manager._remove_install_tree(str(tree))
        assert not tree.exists()
