# SPDX-License-Identifier: 0BSD

"""Load and dispatch Sideband-compatible Python plugins."""

from __future__ import annotations

import os
import shlex
import threading
from typing import Any

from meshchatx.src.backend.plugin_security_scan import assess_sideband_script
from meshchatx.src.backend.plugin_signature import verify_py_signature
from meshchatx.src.backend.sideband_host_adapter import (
    SidebandHostAdapter,
    SimpleTelemeter,
)
from meshchatx.src.backend.sideband_plugins import (
    SidebandCommandPlugin,
    SidebandServicePlugin,
    SidebandTelemetryPlugin,
)

MAX_SIDEBAND_SCRIPT_BYTES = 1_000_000


class SidebandPluginLoader:
    def __init__(self, app: Any):
        self.app = app
        self.host = SidebandHostAdapter(app)
        self.active_command_plugins: dict[str, Any] = {}
        self.active_service_plugins: dict[str, Any] = {}
        self.active_telemetry_plugins: dict[str, Any] = {}
        self.loaded_plugins: list[dict[str, Any]] = []
        self.telemeter = SimpleTelemeter()
        self._lock = threading.RLock()

    def get_config(self) -> dict[str, Any]:
        self.host._refresh_config()
        return dict(self.host.config)

    def set_config(
        self,
        *,
        service_plugins_enabled: bool | None = None,
        command_plugins_enabled: bool | None = None,
        command_plugins_path: str | None = None,
    ) -> dict[str, Any]:
        cfg = getattr(self.app, "config", None)
        if cfg is None:
            raise RuntimeError("config is not available")
        if service_plugins_enabled is not None and hasattr(
            cfg,
            "service_plugins_enabled",
        ):
            cfg.service_plugins_enabled.set(bool(service_plugins_enabled))
        if command_plugins_enabled is not None and hasattr(
            cfg,
            "command_plugins_enabled",
        ):
            cfg.command_plugins_enabled.set(bool(command_plugins_enabled))
        if command_plugins_path is not None and hasattr(cfg, "command_plugins_path"):
            cfg.command_plugins_path.set(command_plugins_path or None)
        return self.reload()

    def list_plugins(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self.loaded_plugins)

    def reload(self) -> dict[str, Any]:
        with self._lock:
            self._stop_all()
            self.active_command_plugins = {}
            self.active_service_plugins = {}
            self.active_telemetry_plugins = {}
            self.loaded_plugins = []
            self.host._refresh_config()
            config = self.host.config
            if not config.get("service_plugins_enabled"):
                return {"config": config, "plugins": [], "loaded": 0}
            path = config.get("command_plugins_path")
            if not path or not os.path.isdir(path):
                return {"config": config, "plugins": [], "loaded": 0}
            for filename in sorted(os.listdir(path)):
                if not filename.lower().endswith(".py"):
                    continue
                self._load_file(os.path.join(path, filename), config)
            enabled_count = sum(
                1 for item in self.loaded_plugins if item.get("enabled")
            )
            return {
                "config": config,
                "plugins": list(self.loaded_plugins),
                "loaded": enabled_count,
            }

    def handle_plugin_command(self, command_string: str, message: Any) -> bool:
        if not command_string:
            return False
        self.host._refresh_config()
        if not self.host.config.get("command_plugins_enabled"):
            return False
        try:
            parts = shlex.split(command_string)
        except ValueError:
            return False
        if not parts:
            return False
        command = parts[0]
        arguments = parts[1:]
        with self._lock:
            plugin = self.active_command_plugins.get(command)
        if plugin is None:
            return False
        plugin.handle_command(arguments, message)
        return True

    def update_telemetry(self, telemeter: Any | None = None) -> dict[str, Any]:
        target = telemeter if telemeter is not None else self.telemeter
        with self._lock:
            plugins = list(self.active_telemetry_plugins.values())
        for plugin in plugins:
            try:
                plugin.update_telemetry(target)
            except Exception:
                continue
        if hasattr(target, "read_all"):
            return target.read_all()
        return {}

    def _stop_all(self) -> None:
        for registry in (
            self.active_command_plugins,
            self.active_service_plugins,
            self.active_telemetry_plugins,
        ):
            for plugin in list(registry.values()):
                try:
                    plugin.stop()
                except Exception:
                    pass

    def _load_file(self, plugin_path: str, config: dict[str, Any]) -> None:
        try:
            size = os.path.getsize(plugin_path)
        except OSError:
            return
        if size <= 0 or size > MAX_SIDEBAND_SCRIPT_BYTES:
            self.loaded_plugins.append(
                {
                    "path": plugin_path,
                    "name": os.path.basename(plugin_path),
                    "type": "unknown",
                    "enabled": False,
                    "error": "script size rejected",
                    "signature": {"present": False, "valid": False, "trusted": False},
                    "security_findings": [],
                },
            )
            return
        try:
            with open(plugin_path, "rb") as handle:
                source_bytes = handle.read()
            source = source_bytes.decode("utf-8")
        except Exception as exc:
            self.loaded_plugins.append(
                {
                    "path": plugin_path,
                    "name": os.path.basename(plugin_path),
                    "type": "unknown",
                    "enabled": False,
                    "error": str(exc),
                    "signature": {"present": False, "valid": False, "trusted": False},
                    "security_findings": [],
                },
            )
            return

        signature = verify_py_signature(plugin_path)
        assessment = assess_sideband_script(plugin_path, source, signature)
        entry = {
            "path": plugin_path,
            "name": os.path.basename(plugin_path),
            "type": "unknown",
            "enabled": False,
            "error": None,
            "signature": signature.to_dict(),
            "security_findings": [item.to_dict() for item in assessment.findings],
            "risk_level": assessment.risk_level,
        }
        if signature.present and not signature.valid:
            entry["error"] = signature.error or "invalid signature"
            self.loaded_plugins.append(entry)
            return

        plugin_globals = {
            "SidebandServicePlugin": SidebandServicePlugin,
            "SidebandCommandPlugin": SidebandCommandPlugin,
            "SidebandTelemetryPlugin": SidebandTelemetryPlugin,
        }
        try:
            exec(source, plugin_globals)
            plugin_class = plugin_globals.get("plugin_class")
            if plugin_class is None:
                entry["error"] = "plugin_class missing"
                self.loaded_plugins.append(entry)
                return
            plugin = plugin_class(self.host)
            plugin.start()
            if not plugin.is_running():
                entry["error"] = "plugin failed to start"
                self.loaded_plugins.append(entry)
                return
            if isinstance(plugin, SidebandCommandPlugin):
                if not config.get("command_plugins_enabled"):
                    entry["type"] = "command"
                    entry["error"] = "command plugins disabled"
                    self.loaded_plugins.append(entry)
                    plugin.stop()
                    return
                name = plugin.command_name
                if not name or name in self.active_command_plugins:
                    entry["type"] = "command"
                    entry["error"] = "duplicate or missing command_name"
                    self.loaded_plugins.append(entry)
                    plugin.stop()
                    return
                self.active_command_plugins[name] = plugin
                entry["type"] = "command"
                entry["plugin_name"] = name
                entry["enabled"] = True
            elif isinstance(plugin, SidebandServicePlugin):
                name = plugin.service_name
                if not name or name in self.active_service_plugins:
                    entry["type"] = "service"
                    entry["error"] = "duplicate or missing service_name"
                    self.loaded_plugins.append(entry)
                    plugin.stop()
                    return
                self.active_service_plugins[name] = plugin
                entry["type"] = "service"
                entry["plugin_name"] = name
                entry["enabled"] = True
            elif isinstance(plugin, SidebandTelemetryPlugin):
                name = plugin.plugin_name
                if not name or name in self.active_telemetry_plugins:
                    entry["type"] = "telemetry"
                    entry["error"] = "duplicate or missing plugin_name"
                    self.loaded_plugins.append(entry)
                    plugin.stop()
                    return
                self.active_telemetry_plugins[name] = plugin
                entry["type"] = "telemetry"
                entry["plugin_name"] = name
                entry["enabled"] = True
            else:
                entry["error"] = "unknown plugin type"
                plugin.stop()
            self.loaded_plugins.append(entry)
        except Exception as exc:
            entry["error"] = str(exc)
            self.loaded_plugins.append(entry)
