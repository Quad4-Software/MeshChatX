# SPDX-License-Identifier: 0BSD

"""Minimal Sideband host surface for MeshChatX plugin execution."""

from __future__ import annotations

from typing import Any


class SidebandHostAdapter:
    def __init__(self, app: Any):
        self.app = app
        self.config: dict[str, Any] = {}
        self._refresh_config()

    def _refresh_config(self) -> None:
        cfg = getattr(self.app, "config", None)
        if cfg is None:
            self.config = {
                "service_plugins_enabled": False,
                "command_plugins_enabled": False,
                "command_plugins_path": None,
                "telemetry_enabled": False,
            }
            return
        path = None
        path_cfg = getattr(cfg, "command_plugins_path", None)
        if path_cfg is not None:
            path = path_cfg.get()
        self.config = {
            "service_plugins_enabled": bool(
                getattr(cfg, "service_plugins_enabled", None)
                and cfg.service_plugins_enabled.get()
            ),
            "command_plugins_enabled": bool(
                getattr(cfg, "command_plugins_enabled", None)
                and cfg.command_plugins_enabled.get()
            ),
            "command_plugins_path": path,
            "telemetry_enabled": bool(
                getattr(cfg, "telemetry_enabled", None) and cfg.telemetry_enabled.get()
            ),
        }

    def send_message(
        self,
        content,
        destination_hash,
        propagation,
        skip_fields=False,
        no_display=False,
        attachment=None,
        image=None,
        audio=None,
    ) -> bool:
        sender = getattr(self.app, "send_message", None)
        if not callable(sender):
            sender = getattr(self.app, "send_lxmf_message", None)
        if not callable(sender):
            return False
        try:
            result = sender(
                content,
                destination_hash,
                propagation,
                skip_fields=skip_fields,
                no_display=no_display,
                attachment=attachment,
                image=image,
                audio=audio,
            )
            return bool(result) if result is not None else True
        except TypeError:
            try:
                result = sender(content, destination_hash, propagation)
                return bool(result) if result is not None else True
            except Exception:
                return False
        except Exception:
            return False


class SimpleTelemeter:
    def __init__(self):
        self.sensors: dict[str, SimpleSensor] = {}

    def enable(self, sensor_name: str) -> None:
        self.synthesize(sensor_name)

    def disable(self, sensor_name: str) -> None:
        self.sensors.pop(sensor_name, None)

    def synthesize(self, sensor_name: str) -> SimpleSensor:
        sensor = self.sensors.get(sensor_name)
        if sensor is None:
            sensor = SimpleSensor(sensor_name)
            self.sensors[sensor_name] = sensor
        return sensor

    def read_all(self) -> dict[str, Any]:
        return {name: sensor.data for name, sensor in self.sensors.items()}


class SimpleSensor:
    def __init__(self, name: str):
        self.name = name
        self.data: dict[str, Any] = {}

    def update_consumer(self, value, type_label: str = "", **kwargs):
        entry = {"value": value, "type_label": type_label, **kwargs}
        self.data.setdefault("consumers", []).append(entry)

    def update_producer(self, value, type_label: str = "", **kwargs):
        entry = {"value": value, "type_label": type_label, **kwargs}
        self.data.setdefault("producers", []).append(entry)

    def update_entry(self, *args, **kwargs):
        self.data.setdefault("entries", []).append({"args": args, "kwargs": kwargs})
