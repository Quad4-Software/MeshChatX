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
        assert "com.meshchatx.mcx-bugs" in ids
        assert "com.meshchatx.transport-node-monitor" not in ids

    def test_enable_disable_plugin(self, tmp_path):
        manager = _make_manager(tmp_path)
        manager.install_bundled_examples()
        plugin_id = "com.meshchatx.mcx-bugs"
        enabled = manager.enable(plugin_id)
        assert enabled["enabled"] is True
        disabled = manager.disable(plugin_id)
        assert disabled["enabled"] is False

    def test_storage_roundtrip(self, tmp_path):
        manager = _make_manager(tmp_path)
        manager.install_bundled_examples()
        plugin_id = "com.meshchatx.mcx-bugs"
        manager.storage_set(plugin_id, "sample_key", json.dumps(["abc123"]))
        value = manager.storage_get(plugin_id, "sample_key")
        assert json.loads(value) == ["abc123"]

    def test_permission_denied_for_manager_capability(self, tmp_path):
        manager = _make_manager(tmp_path)
        manager.install_bundled_examples()
        plugin_id = "com.meshchatx.mcx-bugs"
        manager.enable(plugin_id)
        with pytest.raises(PermissionError):
            manager.call_manager(plugin_id, "unknown.capability", {})

    def test_bug_report_preview_reads_debug_logs(self, tmp_path):
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
        plugin_id = "com.meshchatx.mcx-bugs"
        manager.enable(plugin_id)
        preview = manager.call_manager(
            plugin_id,
            "bugReport.preview",
            {"limit": 10},
        )
        assert preview["line_count"] == 1
        assert "/home/user1/secret" not in preview["log_text"]
        assert "[redacted]" in preview["log_text"]

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
        plugin_id = "com.meshchatx.mcx-bugs"
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
        plugin_id = "com.meshchatx.mcx-bugs"
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
            "../../meshchatx/src/backend/data/plugins/mcx-bugs",
        )
        with pytest.raises(PermissionError):
            manager.install_from_directory(os.path.abspath(source))

    def test_bundled_reinstall_skips_unchanged_and_handles_readonly_tree(
        self,
        tmp_path,
    ):
        manager = _make_manager(tmp_path)
        manager.install_bundled_examples()
        plugin_id = "com.meshchatx.mcx-bugs"
        record = manager._plugins[plugin_id]
        first_hash = record.integrity_hash
        install_path = record.install_path

        for dirpath, dirnames, filenames in os.walk(install_path):
            os.chmod(dirpath, 0o555)
            for name in dirnames:
                os.chmod(os.path.join(dirpath, name), 0o555)
            for name in filenames:
                os.chmod(os.path.join(dirpath, name), 0o444)

        manager.install_bundled_examples()
        assert manager._plugins[plugin_id].integrity_hash == first_hash

        record.version = "0.0.0-test"
        manager.install_bundled_examples()
        assert manager._plugins[plugin_id].version != "0.0.0-test"
        assert os.path.isdir(manager._plugins[plugin_id].install_path)
