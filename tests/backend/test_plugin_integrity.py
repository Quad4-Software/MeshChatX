# SPDX-License-Identifier: 0BSD

import json

from meshchatx.src.backend.plugin_integrity import INTEGRITY_TAMPER_MESSAGE
from meshchatx.src.backend.plugin_manager import PluginManager


def _install_simple(manager, tmp_path):
    source = tmp_path / "src"
    source.mkdir()
    (source / "plugin.json").write_text(
        json.dumps(
            {
                "id": "com.example.integrity",
                "version": "1.0.0",
                "apiVersion": 1,
                "name": "Integrity",
                "frontend": {"entry": "frontend/main.js", "type": "js"},
            }
        ),
        encoding="utf-8",
    )
    frontend = source / "frontend"
    frontend.mkdir()
    (frontend / "main.js").write_text("export default {}", encoding="utf-8")
    return manager.install_from_directory(str(source))


def test_tamper_disables_and_reenable_refreshes_hash(tmp_path):
    manager = PluginManager(str(tmp_path / "storage"))
    installed = _install_simple(manager, tmp_path)
    plugin_id = installed["id"]
    manager.enable(plugin_id)
    assert manager.get_plugin(plugin_id)["enabled"] is True

    target = (
        tmp_path
        / "storage"
        / "plugins"
        / "installed"
        / plugin_id
        / "frontend"
        / "main.js"
    )
    target.write_text("export default {tampered:true}", encoding="utf-8")

    reloaded = PluginManager(str(tmp_path / "storage"))
    view = reloaded.get_plugin(plugin_id)
    assert view is not None
    assert view["enabled"] is False
    assert view["tampered"] is True
    assert INTEGRITY_TAMPER_MESSAGE in (view["auto_disabled_reason"] or "")

    enabled = reloaded.enable(plugin_id)
    assert enabled["enabled"] is True
    assert enabled["tampered"] is False
