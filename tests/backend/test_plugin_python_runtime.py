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
