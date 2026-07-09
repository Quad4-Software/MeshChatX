# SPDX-License-Identifier: 0BSD

from __future__ import annotations


class SidebandPlugin:
    pass


class SidebandCommandPlugin(SidebandPlugin):
    command_name = ""

    def __init__(self, sideband_core):
        self._sideband = sideband_core
        self._started = False

    def start(self) -> None:
        self._started = True

    def stop(self) -> None:
        self._started = False

    def is_running(self) -> bool:
        return self._started

    def get_sideband(self):
        return self._sideband

    def handle_command(self, arguments, lxm):
        raise NotImplementedError


class SidebandServicePlugin(SidebandPlugin):
    service_name = ""

    def __init__(self, sideband_core):
        self._sideband = sideband_core
        self._started = False

    def start(self) -> None:
        self._started = True

    def stop(self) -> None:
        self._started = False

    def is_running(self) -> bool:
        return self._started

    def get_sideband(self):
        return self._sideband


class SidebandTelemetryPlugin(SidebandPlugin):
    plugin_name = ""

    def __init__(self, sideband_core):
        self._sideband = sideband_core
        self._started = False

    def start(self) -> None:
        self._started = True

    def stop(self) -> None:
        self._started = False

    def is_running(self) -> bool:
        return self._started

    def get_sideband(self):
        return self._sideband

    def update_telemetry(self, telemeter):
        raise NotImplementedError
