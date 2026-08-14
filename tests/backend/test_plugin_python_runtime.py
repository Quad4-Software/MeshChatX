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
        granted_permissions=["storage:isolated"],
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
