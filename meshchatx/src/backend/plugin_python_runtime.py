# SPDX-License-Identifier: 0BSD

from __future__ import annotations

import importlib.util
import json
import sys
import threading
from typing import Any, Callable

from meshchatx.src.backend.plugin_guard import validate_invoke_payload


class PluginPythonHost:
    def __init__(
        self,
        plugin_id: str,
        *,
        log: Callable[[str], None],
        call_manager: Callable[[str, dict[str, Any]], Any],
        storage_get: Callable[[str], str | None],
        storage_set: Callable[[str, str], None],
        network_fetch_allowed: Callable[[], bool],
    ):
        self.plugin_id = plugin_id
        self._log = log
        self._call_manager = call_manager
        self._storage_get = storage_get
        self._storage_set = storage_set
        self._network_fetch_allowed = network_fetch_allowed
        self._logs: list[str] = []

    def log(self, message: str) -> None:
        self._logs.append(str(message))
        self._log(str(message))

    def call_manager(self, capability: str, args: dict[str, Any] | None = None) -> Any:
        return self._call_manager(capability, args or {})

    def storage_get(self, key: str) -> str | None:
        return self._storage_get(key)

    def storage_set(self, key: str, value: str) -> None:
        self._storage_set(key, value)

    def network_fetch_allowed(self) -> bool:
        return self._network_fetch_allowed()

    def drain_logs(self) -> list[str]:
        logs = list(self._logs)
        self._logs.clear()
        return logs


class PluginPythonRuntime:
    def __init__(self):
        self._lock = threading.RLock()
        self._modules: dict[str, Any] = {}

    def unload(self, plugin_id: str) -> None:
        with self._lock:
            module = self._modules.pop(plugin_id, None)
            if module is None:
                return
            deactivate = getattr(module, "deactivate", None)
            if callable(deactivate):
                try:
                    deactivate()
                except Exception:
                    pass

    def _load_module(self, plugin_id: str, entry_path: str) -> Any:
        with self._lock:
            module = self._modules.get(plugin_id)
            if module is not None:
                return module
            spec = importlib.util.spec_from_file_location(
                f"meshchatx_plugin_{plugin_id}", entry_path
            )
            if spec is None or spec.loader is None:
                raise ImportError(f"cannot load python backend: {entry_path}")
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
            self._modules[plugin_id] = module
            return module

    def activate(self, plugin_id: str, entry_path: str, host: PluginPythonHost) -> None:
        module = self._load_module(plugin_id, entry_path)
        activate = getattr(module, "activate", None)
        if callable(activate):
            activate(host)

    def on_hook(
        self,
        plugin_id: str,
        entry_path: str,
        hook: str,
        payload: dict[str, Any],
        host: PluginPythonHost,
    ) -> Any:
        module = self._load_module(plugin_id, entry_path)
        handler = getattr(module, "on_hook", None)
        if not callable(handler):
            return None
        return handler(hook, payload, host)

    def invoke(
        self,
        plugin_id: str,
        entry_path: str,
        method: str,
        args: dict[str, Any],
        host: PluginPythonHost,
    ) -> Any:
        module = self._load_module(plugin_id, entry_path)
        handler = getattr(module, "invoke", None)
        if not callable(handler):
            raise ValueError(f"unknown method: {method}")
        payload = json.dumps({"method": method, "args": args}).encode("utf-8")
        validate_invoke_payload(payload)
        result = handler(method, args or {}, host)
        logs = host.drain_logs()
        if isinstance(result, dict):
            result.setdefault("logs", logs)
            return result
        return {"ok": True, "result": result, "logs": logs}
