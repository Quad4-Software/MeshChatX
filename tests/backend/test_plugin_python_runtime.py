# SPDX-License-Identifier: 0BSD

import json

import pytest

from meshchatx.src.backend.plugin_manager import PluginManager

PYTHON_BACKEND = """
def activate(host):
    host.storage_set("activated", "1")

def invoke(method, args, host=None):
    if host is None:
        host = args
        args = method
        method = "invoke"
    if method == "echo":
        return {"echo": args.get("value"), "activated": host.storage_get("activated")}
    raise ValueError("unknown")

def on_hook(hook, payload, host):
    host.storage_set("last_hook", hook)
    return {"hook": hook}
"""


def test_python_backend_grants_invoke_hooks(tmp_path):
    source = tmp_path / "src"
    source.mkdir()
    (source / "plugin.json").write_text(
        json.dumps(
            {
                "id": "com.example.python",
                "version": "1.0.0",
                "apiVersion": 1,
                "name": "Python Plugin",
                "backend": {"entry": "backend/main.py", "type": "python"},
                "permissions": {
                    "hooks": ["announce.received"],
                    "storage": "isolated",
                    "managers": ["destinationPath.read"],
                },
            },
        ),
        encoding="utf-8",
    )
    backend = source / "backend"
    backend.mkdir()
    (backend / "main.py").write_text(PYTHON_BACKEND, encoding="utf-8")

    class FakeApp:
        reticulum = object()
        rnpath_handler = None
        plugins_enabled = True

    manager = PluginManager(str(tmp_path / "storage"), app=FakeApp())
    installed = manager.install_from_directory(
        str(source),
        granted_permissions=[
            "backend:python",
            "hooks:announce.received",
            "storage:isolated",
            "managers:destinationPath.read",
        ],
    )
    assert installed["backend_type"] == "python"
    enabled = manager.enable("com.example.python")
    assert enabled["enabled"] is True
    assert manager.storage_get("com.example.python", "activated") == "1"

    result = manager.invoke("com.example.python", "echo", {"value": "hi"})
    assert result["echo"] == "hi"
    assert result["activated"] == "1"

    manager.dispatch_hook("com.example.python", "announce.received", {"x": 1})
    assert manager.storage_get("com.example.python", "last_hook") == "announce.received"

    with pytest.raises(PermissionError):
        manager.call_manager("com.example.python", "rnsLink.open", {})


def test_python_runtime_purges_pycache_on_load(tmp_path):
    source = tmp_path / "src"
    source.mkdir()
    (source / "plugin.json").write_text(
        json.dumps(
            {
                "id": "com.example.python-cache",
                "version": "1.0.0",
                "apiVersion": 1,
                "name": "Python Cache",
                "backend": {"entry": "backend/main.py", "type": "python"},
                "permissions": {"storage": "isolated"},
            },
        ),
        encoding="utf-8",
    )
    backend = source / "backend"
    backend.mkdir()
    (backend / "main.py").write_text(PYTHON_BACKEND, encoding="utf-8")
    cache = backend / "__pycache__"
    cache.mkdir()
    planted = cache / "main.cpython-314.pyc"
    planted.write_bytes(b"not-real-bytecode")

    class FakeApp:
        reticulum = object()
        rnpath_handler = None
        plugins_enabled = True

    manager = PluginManager(str(tmp_path / "storage"), app=FakeApp())
    manager.install_from_directory(
        str(source),
        granted_permissions=["backend:python", "storage:isolated"],
    )
    installed_cache = (
        tmp_path
        / "storage"
        / "plugins"
        / "installed"
        / "com.example.python-cache"
        / "backend"
        / "__pycache__"
    )
    installed_cache.mkdir(parents=True, exist_ok=True)
    planted_installed = installed_cache / "main.cpython-314.pyc"
    planted_installed.write_bytes(b"not-real-bytecode")
    manager.enable("com.example.python-cache")
    assert not planted_installed.exists()
    assert not installed_cache.exists()


def test_python_backend_requires_explicit_in_process_permission(tmp_path):
    source = tmp_path / "src"
    source.mkdir()
    (source / "plugin.json").write_text(
        json.dumps(
            {
                "id": "com.example.python-consent",
                "version": "1.0.0",
                "apiVersion": 1,
                "name": "Python Consent",
                "backend": {"entry": "backend/main.py", "type": "python"},
            }
        ),
        encoding="utf-8",
    )
    backend = source / "backend"
    backend.mkdir()
    (backend / "main.py").write_text(
        "def activate(host):\n    host.log('activated')\n",
        encoding="utf-8",
    )

    class FakeApp:
        reticulum = object()
        rnpath_handler = None
        plugins_enabled = True

    manager = PluginManager(str(tmp_path / "storage"), app=FakeApp())
    installed = manager.install_from_directory(str(source))
    assert "backend:python" not in installed["granted_permissions"]
    with pytest.raises(PermissionError, match="backend execution permission"):
        manager.enable(installed["id"])

    installed = manager.install_from_directory(
        str(source),
        granted_permissions=["backend:python"],
    )
    assert "backend:python" in installed["granted_permissions"]
    assert installed["enabled"] is True


def test_reinstalling_enabled_python_backend_reactivates_it(tmp_path):
    source = tmp_path / "src"
    source.mkdir()
    (source / "plugin.json").write_text(
        json.dumps(
            {
                "id": "com.example.python-update",
                "version": "1.0.0",
                "apiVersion": 1,
                "name": "Python Update",
                "backend": {"entry": "backend/main.py", "type": "python"},
                "permissions": {"storage": "isolated"},
            }
        ),
        encoding="utf-8",
    )
    backend = source / "backend"
    backend.mkdir()
    entry = backend / "main.py"
    entry.write_text(
        "def activate(host):\n"
        "    host.storage_set('activations', str(int(host.storage_get('activations') or '0') + 1))\n",
        encoding="utf-8",
    )

    class FakeApp:
        reticulum = object()
        rnpath_handler = None
        plugins_enabled = True

    manager = PluginManager(str(tmp_path / "storage"), app=FakeApp())
    grants = ["backend:python", "storage:isolated"]
    installed = manager.install_from_directory(str(source), granted_permissions=grants)
    manager.enable(installed["id"])
    assert manager.storage_get(installed["id"], "activations") == "1"

    entry.write_text(
        "def activate(host):\n"
        "    host.storage_set('activations', str(int(host.storage_get('activations') or '0') + 1))\n"
        "    host.storage_set('updated', '1')\n",
        encoding="utf-8",
    )
    updated = manager.install_from_directory(str(source), granted_permissions=grants)
    assert updated["enabled"] is True
    assert manager.storage_get(installed["id"], "activations") == "2"
    assert manager.storage_get(installed["id"], "updated") == "1"


def test_legacy_enabled_python_backend_is_disabled_without_explicit_grant(tmp_path):
    source = tmp_path / "src"
    source.mkdir()
    (source / "plugin.json").write_text(
        json.dumps(
            {
                "id": "com.example.python-legacy",
                "version": "1.0.0",
                "apiVersion": 1,
                "name": "Legacy Python",
                "backend": {"entry": "backend/main.py", "type": "python"},
            }
        ),
        encoding="utf-8",
    )
    backend = source / "backend"
    backend.mkdir()
    (backend / "main.py").write_text(
        "def activate(host):\n    pass\n", encoding="utf-8"
    )

    class FakeApp:
        reticulum = object()
        rnpath_handler = None
        plugins_enabled = True

    storage = tmp_path / "storage"
    manager = PluginManager(str(storage), app=FakeApp())
    installed = manager.install_from_directory(
        str(source),
        granted_permissions=["backend:python"],
    )
    manager.enable(installed["id"])
    manager._write_plugin_state(
        installed["id"],
        True,
        None,
        granted_permissions=[],
        tampered=False,
    )

    reloaded = PluginManager(str(storage), app=FakeApp())
    migrated = reloaded.get_plugin(installed["id"])
    assert migrated["enabled"] is False
    assert "backend execution permission" in migrated["auto_disabled_reason"]
