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
            },
        ),
        encoding="utf-8",
    )
    frontend = source / "frontend"
    frontend.mkdir()
    (frontend / "main.js").write_text("export default {}", encoding="utf-8")
    return manager.install_from_directory(str(source))


def test_tamper_disables_and_reenable_refuses_without_reinstall(tmp_path):
    from meshchatx.src.backend.plugin_guard import PluginSecurityError

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

    try:
        reloaded.enable(plugin_id)
        raise AssertionError("enable must refuse tampered plugin trees")
    except PluginSecurityError as exc:
        assert "tampered" in str(exc).lower()
    still = reloaded.get_plugin(plugin_id)
    assert still["enabled"] is False
    assert still["tampered"] is True


PYTHON_BACKEND = """
def invoke(method, args, host=None):
    if method == "echo":
        return {"echo": args.get("value")}
    raise ValueError("unknown")

def on_hook(hook, payload, host):
    host.storage_set("last_hook", hook)
    return {"hook": hook}
"""


def _install_python(manager, tmp_path):
    source = tmp_path / "python-src"
    source.mkdir()
    (source / "plugin.json").write_text(
        json.dumps(
            {
                "id": "com.example.integrity-py",
                "version": "1.0.0",
                "apiVersion": 1,
                "name": "Integrity Python",
                "backend": {"entry": "backend/main.py", "type": "python"},
                "permissions": {
                    "hooks": ["announce.received"],
                    "storage": "isolated",
                },
            },
        ),
        encoding="utf-8",
    )
    backend = source / "backend"
    backend.mkdir()
    (backend / "main.py").write_text(PYTHON_BACKEND, encoding="utf-8")
    return manager.install_from_directory(
        str(source),
        granted_permissions=["hooks:announce.received", "storage:isolated"],
    )


def test_invoke_refuses_live_tamper_without_reinstall(tmp_path):
    from meshchatx.src.backend.plugin_guard import PluginSecurityError

    class FakeApp:
        reticulum = object()
        rnpath_handler = None
        plugins_enabled = True

    manager = PluginManager(str(tmp_path / "storage"), app=FakeApp())
    installed = _install_python(manager, tmp_path)
    plugin_id = installed["id"]
    manager.enable(plugin_id)
    assert manager.invoke(plugin_id, "echo", {"value": "ok"})["echo"] == "ok"

    target = (
        tmp_path
        / "storage"
        / "plugins"
        / "installed"
        / plugin_id
        / "backend"
        / "main.py"
    )
    target.write_text(
        "def invoke(method, args, host=None):\n    return {'echo': 'pwned'}\n",
        encoding="utf-8",
    )

    try:
        manager.invoke(plugin_id, "echo", {"value": "ok"})
        raise AssertionError("invoke must refuse a tampered plugin tree")
    except PluginSecurityError as exc:
        assert "tampered" in str(exc).lower()
    view = manager.get_plugin(plugin_id)
    assert view["enabled"] is False
    assert view["tampered"] is True


def test_dispatch_hook_skips_live_tamper(tmp_path):
    class FakeApp:
        reticulum = object()
        rnpath_handler = None
        plugins_enabled = True

    manager = PluginManager(str(tmp_path / "storage"), app=FakeApp())
    installed = _install_python(manager, tmp_path)
    plugin_id = installed["id"]
    manager.enable(plugin_id)

    target = (
        tmp_path
        / "storage"
        / "plugins"
        / "installed"
        / plugin_id
        / "backend"
        / "main.py"
    )
    target.write_text(
        "def on_hook(hook, payload, host):\n    host.storage_set('last_hook', 'pwned')\n",
        encoding="utf-8",
    )

    manager.dispatch_hook(plugin_id, "announce.received", {"x": 1})
    assert manager.storage_get(plugin_id, "last_hook") is None
    view = manager.get_plugin(plugin_id)
    assert view["enabled"] is False
    assert view["tampered"] is True
