# SPDX-License-Identifier: 0BSD

import json
import os

import pytest


def _make_manager(tmp_path, app=None):
    from meshchatx.src.backend.plugin_manager import PluginManager

    return PluginManager(str(tmp_path), app=app)


class TestPluginManagerInstall:
    def test_install_bundled_example(self, tmp_path):
        manager = _make_manager(tmp_path)
        manager.install_bundled_examples()
        plugins = manager.list_plugins()
        ids = [plugin["id"] for plugin in plugins]
        assert "com.meshchatx.mcx-hello" in ids
        assert "com.meshchatx.transport-node-monitor" not in ids

    def test_enable_disable_plugin(self, tmp_path):
        manager = _make_manager(tmp_path)
        manager.install_bundled_examples()
        plugin_id = "com.meshchatx.mcx-hello"
        enabled = manager.enable(plugin_id)
        assert enabled["enabled"] is True
        disabled = manager.disable(plugin_id)
        assert disabled["enabled"] is False

    def test_storage_roundtrip(self, tmp_path):
        manager = _make_manager(tmp_path)
        manager.install_bundled_examples()
        plugin_id = "com.meshchatx.mcx-hello"
        manager.enable(plugin_id)
        manager.storage_set(plugin_id, "sample_key", json.dumps(["abc123"]))
        value = manager.storage_get(plugin_id, "sample_key")
        assert json.loads(value) == ["abc123"]

    def test_permission_denied_for_manager_capability(self, tmp_path):
        manager = _make_manager(tmp_path)
        manager.install_bundled_examples()
        plugin_id = "com.meshchatx.mcx-hello"
        manager.enable(plugin_id)
        with pytest.raises(PermissionError):
            manager.call_manager(plugin_id, "unknown.capability", {})

    def test_debug_log_read_redacts_secrets(self, tmp_path, monkeypatch):
        # The manager prefers the process-global memory handler. Clear it so
        # the fake database path is what the capability actually reads.
        from meshchatx.src.backend import persistent_log_handler as plh

        monkeypatch.setattr(plh, "memory_log_handler", None)

        class FakeLogs:
            def get_logs(self, **_kwargs):
                return [
                    {
                        "timestamp": 1.0,
                        "level": "INFO",
                        "module": "meshchat",
                        "message": "peer aa" + ("bb" * 15) + " at /home/user1/secret",
                    },
                ]

            def get_total_count(self, **_kwargs):
                return 1

        class FakeDatabase:
            debug_logs = FakeLogs()

        class FakeApp:
            reticulum = object()
            database = FakeDatabase()
            storage_dir = str(tmp_path)
            current_context = None

        manager = _make_manager(tmp_path, app=FakeApp())
        manager.install_bundled_examples()
        plugin_id = "com.meshchatx.mcx-hello"
        manager.enable(plugin_id)
        # The minimal example declares no manager permissions, so grant the
        # capability under test directly.
        record = manager._plugins[plugin_id]
        record.manifest.setdefault("permissions", {})["managers"] = [
            "debugLog.read",
        ]
        record.granted_permissions = [
            "managers:debugLog.read",
        ]
        result = manager.call_manager(
            plugin_id,
            "debugLog.read",
            {"limit": 10},
        )
        assert result["total"] == 1
        assert "/home/user1/secret" not in result["logs"][0]["message"]
        assert "[redacted]" in result["logs"][0]["message"]

    def test_rns_link_capabilities_require_manifest_grant(self, tmp_path):
        class FakeLinkManager:
            async def open_link(self, *_args, **_kwargs):
                return object(), False, None

            def identify(self, *_args, **_kwargs):
                return True, None

            def close(self, *_args, **_kwargs):
                return True

        class FakeApp:
            reticulum = object()
            rns_link_manager = FakeLinkManager()

        manager = _make_manager(tmp_path, app=FakeApp())
        manager.install_bundled_examples()
        plugin_id = "com.meshchatx.mcx-hello"
        manager.enable(plugin_id)
        with pytest.raises(PermissionError):
            manager.call_manager(
                plugin_id,
                "rnsLink.open",
                {"destination_hash": "aa" * 16, "aspect": "microrn.mgmt"},
            )

        record = manager._plugins[plugin_id]
        record.manifest.setdefault("permissions", {})["managers"] = [
            "destinationPath.read",
            "rnsLink.open",
            "rnsLink.close",
        ]
        record.granted_permissions = [
            "managers:destinationPath.read",
            "managers:rnsLink.open",
            "managers:rnsLink.close",
        ]
        opened = manager.call_manager(
            plugin_id,
            "rnsLink.open",
            {"destination_hash": "aa" * 16, "aspect": "microrn.mgmt"},
        )
        assert opened["ok"] is True
        closed = manager.call_manager(
            plugin_id,
            "rnsLink.close",
            {"destination_hash": "aa" * 16, "aspect": "microrn.mgmt"},
        )
        assert closed["ok"] is True

    def test_rns_link_event_hook_dispatches(self, tmp_path):
        events = []

        class FakeApp:
            plugins_enabled = True

            def websocket_broadcast(self, _message):
                return None

        manager = _make_manager(tmp_path, app=FakeApp())
        manager.install_bundled_examples()
        plugin_id = "com.meshchatx.mcx-hello"
        manager.enable(plugin_id)
        record = manager._plugins[plugin_id]
        record.manifest.setdefault("permissions", {})["hooks"] = [
            "announce.received",
            "rns.link.event",
        ]
        record.granted_permissions = [
            "hooks:announce.received",
            "hooks:rns.link.event",
        ]
        manager.dispatch_hook = lambda pid, hook, payload: events.append(
            (pid, hook, payload),
        )
        manager.on_rns_link_event(
            {
                "type": "rns.link.event",
                "event": "link_closed",
                "destination_hash": "aa" * 16,
                "aspect": "microrn.mgmt",
            },
        )
        assert events == [
            (
                plugin_id,
                "rns.link.event",
                {
                    "event": "link_closed",
                    "destination_hash": "aa" * 16,
                    "aspect": "microrn.mgmt",
                    "payload_b64": None,
                },
            ),
        ]

    def test_manifest_validation_rejects_invalid_id(self, tmp_path):
        manager = _make_manager(tmp_path)
        plugin_dir = os.path.join(tmp_path, "bad-plugin")
        os.makedirs(plugin_dir, exist_ok=True)
        with open(
            os.path.join(plugin_dir, "plugin.json"),
            "w",
            encoding="utf-8",
        ) as handle:
            json.dump({"id": "bad id", "version": "1.0.0", "apiVersion": 1}, handle)
        with pytest.raises(ValueError):
            manager.install_from_directory(plugin_dir)

    def test_plugins_disabled_blocks_install_and_enable(self, tmp_path):
        class DisabledApp:
            plugins_enabled = False

        manager = _make_manager(tmp_path, app=DisabledApp())
        manager.install_bundled_examples()
        assert manager.list_plugins() == []
        source = os.path.join(
            os.path.dirname(__file__),
            "../../meshchatx/src/backend/data/plugins/mcx-hello",
        )
        with pytest.raises(PermissionError):
            manager.install_from_directory(os.path.abspath(source))

    def test_bundled_reinstall_skips_unchanged_and_handles_readonly_tree(
        self,
        tmp_path,
    ):
        manager = _make_manager(tmp_path)
        manager.install_bundled_examples()
        plugin_id = "com.meshchatx.mcx-hello"
        record = manager._plugins[plugin_id]
        first_hash = record.integrity_hash
        install_path = record.install_path

        for dirpath, dirnames, filenames in os.walk(install_path):
            os.chmod(dirpath, 0o550)
            for name in dirnames:
                os.chmod(os.path.join(dirpath, name), 0o550)
            for name in filenames:
                os.chmod(os.path.join(dirpath, name), 0o444)

        manager.install_bundled_examples()
        assert manager._plugins[plugin_id].integrity_hash == first_hash

        record.version = "0.0.0-test"
        manager.install_bundled_examples()
        assert manager._plugins[plugin_id].version != "0.0.0-test"
        assert os.path.isdir(manager._plugins[plugin_id].install_path)


class TestPluginAppManagers:
    def _enabled_plugin(self, manager):
        manager.install_bundled_examples()
        plugin_id = "com.meshchatx.mcx-hello"
        manager.enable(plugin_id)
        return plugin_id

    def _grant(self, manager, plugin_id, managers):
        record = manager._plugins[plugin_id]
        record.manifest.setdefault("permissions", {})["managers"] = list(managers)
        record.granted_permissions = [f"managers:{m}" for m in managers]

    def test_new_managers_require_manifest_grant(self, tmp_path):
        class FakeApp:
            reticulum = object()

        manager = _make_manager(tmp_path, app=FakeApp())
        plugin_id = self._enabled_plugin(manager)
        for capability in (
            "status.read",
            "contacts.read",
            "nodes.read",
            "conversations.list",
            "messages.read",
            "message.send",
            "telemetry.read",
        ):
            with pytest.raises(PermissionError):
                manager.call_manager(plugin_id, capability, {})

    def test_status_read_returns_safe_snapshot(self, tmp_path):
        class FakeApp:
            reticulum = object()
            plugins_enabled = True
            config = None

        manager = _make_manager(tmp_path, app=FakeApp())
        plugin_id = self._enabled_plugin(manager)
        self._grant(manager, plugin_id, ["status.read"])
        result = manager.call_manager(plugin_id, "status.read", {})
        assert result["ok"] is True
        assert "counts" in result
        assert "privacy_mode" in result

    def test_message_send_validates_destination(self, tmp_path):
        sent = []

        class FakeApp:
            reticulum = object()
            demo_mode = False
            plugins_enabled = True

            async def send_message(self, **kwargs):
                sent.append(kwargs)
                return {"hash": b"\x01" * 32}

        manager = _make_manager(tmp_path, app=FakeApp())
        plugin_id = self._enabled_plugin(manager)
        self._grant(manager, plugin_id, ["message.send"])
        with pytest.raises(ValueError, match="destination_hash"):
            manager.call_manager(
                plugin_id,
                "message.send",
                {"destination_hash": "not-hex", "content": "hi"},
            )
        with pytest.raises(ValueError, match="content"):
            manager.call_manager(
                plugin_id,
                "message.send",
                {"destination_hash": "ab" * 32, "content": 123},
            )
        result = manager.call_manager(
            plugin_id,
            "message.send",
            {"destination_hash": "ab" * 32, "content": "hello"},
        )
        assert result["ok"] is True
        assert sent and sent[0]["destination_hash"] == "ab" * 32

    def test_message_send_blocked_in_demo_mode(self, tmp_path):
        class FakeApp:
            reticulum = object()
            demo_mode = True
            plugins_enabled = True

            async def send_message(self, **_kwargs):  # pragma: no cover
                raise AssertionError("must not send")

        manager = _make_manager(tmp_path, app=FakeApp())
        plugin_id = self._enabled_plugin(manager)
        self._grant(manager, plugin_id, ["message.send"])
        with pytest.raises(PermissionError, match="demo mode"):
            manager.call_manager(
                plugin_id,
                "message.send",
                {"destination_hash": "ab" * 32, "content": "hi"},
            )

    def test_messages_read_requires_peer_hash(self, tmp_path):
        class FakeHandler:
            def get_conversation_messages(self, *_args, **_kwargs):
                return []

            def get_conversations(self, *_args, **_kwargs):
                return []

        class FakeApp:
            reticulum = object()
            message_handler = FakeHandler()
            plugins_enabled = True

        manager = _make_manager(tmp_path, app=FakeApp())
        plugin_id = self._enabled_plugin(manager)
        self._grant(manager, plugin_id, ["messages.read", "conversations.list"])
        with pytest.raises(ValueError, match="peer_hash"):
            manager.call_manager(plugin_id, "messages.read", {})
        result = manager.call_manager(
            plugin_id,
            "messages.read",
            {"peer_hash": "cd" * 32, "limit": 10},
        )
        assert result["messages"] == []
        convos = manager.call_manager(plugin_id, "conversations.list", {"limit": 5})
        assert convos["conversations"] == []

    def test_message_send_rejects_oversized_and_bad_fields(self, tmp_path):
        class FakeApp:
            reticulum = object()
            demo_mode = False
            plugins_enabled = True

            async def send_message(self, **_kwargs):  # pragma: no cover
                raise AssertionError("must not send")

        manager = _make_manager(tmp_path, app=FakeApp())
        plugin_id = self._enabled_plugin(manager)
        self._grant(manager, plugin_id, ["message.send"])
        with pytest.raises(ValueError, match="128 KiB"):
            manager.call_manager(
                plugin_id,
                "message.send",
                {
                    "destination_hash": "ab" * 32,
                    "content": "x" * (128 * 1024 + 1),
                },
            )
        with pytest.raises(ValueError, match="title"):
            manager.call_manager(
                plugin_id,
                "message.send",
                {
                    "destination_hash": "ab" * 32,
                    "content": "hi",
                    "title": "t" * 501,
                },
            )
        with pytest.raises(ValueError, match="reply_to_hash"):
            manager.call_manager(
                plugin_id,
                "message.send",
                {
                    "destination_hash": "ab" * 32,
                    "content": "hi",
                    "reply_to_hash": "zz",
                },
            )

    def test_telemetry_read_shapes_rows_without_raw_blob(self, tmp_path):
        from meshchatx.src.backend.telemetry_utils import Telemeter

        packed = Telemeter.pack(
            time_utc=1700000000,
            battery={"charge_percent": 88, "charging": True},
        )

        class FakeTelemetry:
            def get_telemetry_history(self, destination_hash, **kwargs):
                return [
                    {
                        "id": 7,
                        "destination_hash": destination_hash,
                        "timestamp": 1700000000.0,
                        "data": packed,
                        "received_from": "deadbeef",
                        "physical_link": '{"rssi": -40}',
                        "created_at": "2024-01-01 00:00:00",
                        "updated_at": "2024-01-01 00:00:01",
                    }
                ]

            def get_all_latest_telemetry(self):
                return []

        class FakeDatabase:
            telemetry = FakeTelemetry()

        class FakeApp:
            reticulum = object()
            database = FakeDatabase()
            plugins_enabled = True

        manager = _make_manager(tmp_path, app=FakeApp())
        plugin_id = self._enabled_plugin(manager)
        self._grant(manager, plugin_id, ["telemetry.read"])
        result = manager.call_manager(
            plugin_id,
            "telemetry.read",
            {"destination_hash": "ab" * 32},
        )
        row = result["telemetry"][0]
        # Raw storage columns must not leak through.
        assert "data" not in row
        assert "received_from" not in row
        assert "id" not in row
        assert row["telemetry"]["battery"]["charge_percent"] == 88
        assert row["physical_link"] == {"rssi": -40}

    def test_conversations_list_omits_message_bodies(self, tmp_path):
        class FakeHandler:
            def get_conversations(self, *_args, **_kwargs):
                return [
                    {
                        "peer_hash": "ab" * 32,
                        "state": "delivered",
                        "title": "hello",
                        "content": "secret body that must not leak",
                        "has_attachments": 1,
                    }
                ]

            def get_conversation_messages(self, *_args, **_kwargs):
                return []

        class FakeApp:
            reticulum = object()
            message_handler = FakeHandler()
            plugins_enabled = True

        manager = _make_manager(tmp_path, app=FakeApp())
        plugin_id = self._enabled_plugin(manager)
        self._grant(manager, plugin_id, ["conversations.list"])
        result = manager.call_manager(plugin_id, "conversations.list", {})
        row = result["conversations"][0]
        assert "content" not in row
        assert row["title"] == "hello"
        assert row["has_attachments"] == 1

    def test_storage_get_rejects_bad_key(self, tmp_path):
        manager, plugin_id = _storage_plugin_grant(tmp_path)
        with pytest.raises(ValueError, match="storage key"):
            manager.storage_get(plugin_id, "")
        with pytest.raises(ValueError, match="storage key"):
            manager.storage_get(plugin_id, 123)
        with pytest.raises(ValueError, match="storage key"):
            manager.storage_delete(plugin_id, "k" * 300)


def _storage_plugin_grant(tmp_path):
    from meshchatx.src.backend.plugin_manager import PluginManager

    source = tmp_path / "src2"
    source.mkdir(exist_ok=True)
    (source / "plugin.json").write_text(
        json.dumps(
            {
                "id": "com.example.storage-two",
                "version": "1.0.0",
                "apiVersion": 1,
                "permissions": {"storage": "isolated"},
            },
        ),
        encoding="utf-8",
    )
    manager = PluginManager(str(tmp_path / "storage2"))
    installed = manager.install_from_directory(
        str(source),
        granted_permissions=["storage:isolated"],
    )
    manager.enable(installed["id"])
    return manager, installed["id"]
