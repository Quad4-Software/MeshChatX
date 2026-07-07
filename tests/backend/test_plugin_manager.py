# SPDX-License-Identifier: 0BSD

import json
import os
import tempfile

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
        assert "com.meshchatx.transport-node-monitor" in ids

    def test_enable_disable_plugin(self, tmp_path):
        manager = _make_manager(tmp_path)
        manager.install_bundled_examples()
        plugin_id = "com.meshchatx.transport-node-monitor"
        enabled = manager.enable(plugin_id)
        assert enabled["enabled"] is True
        disabled = manager.disable(plugin_id)
        assert disabled["enabled"] is False

    def test_invoke_storage_roundtrip(self, tmp_path):
        manager = _make_manager(tmp_path)
        manager.install_bundled_examples()
        plugin_id = "com.meshchatx.transport-node-monitor"
        manager.enable(plugin_id)
        manager.invoke(plugin_id, "setWatchedNodes", {"nodes": ["abc123"]})
        state = manager.invoke(plugin_id, "getState")
        assert state["watched_nodes"] == ["abc123"]

    def test_permission_denied_for_manager_capability(self, tmp_path):
        manager = _make_manager(tmp_path)
        manager.install_bundled_examples()
        plugin_id = "com.meshchatx.transport-node-monitor"
        manager.enable(plugin_id)
        with pytest.raises(PermissionError):
            manager.call_manager(plugin_id, "unknown.capability", {})

    def test_manifest_validation_rejects_invalid_id(self, tmp_path):
        manager = _make_manager(tmp_path)
        plugin_dir = os.path.join(tmp_path, "bad-plugin")
        os.makedirs(plugin_dir, exist_ok=True)
        with open(os.path.join(plugin_dir, "plugin.json"), "w", encoding="utf-8") as handle:
            json.dump({"id": "bad id", "version": "1.0.0", "apiVersion": 1}, handle)
        with pytest.raises(ValueError):
            manager.install_from_directory(plugin_dir)
