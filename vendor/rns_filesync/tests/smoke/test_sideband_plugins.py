"""Smoke checks for Sideband drop-in plugins."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

pytestmark = [pytest.mark.smoke, pytest.mark.unit]

ROOT = Path(__file__).resolve().parents[2]
SERVICE_PLUGIN = ROOT / "sideband" / "rns_filesync_service.py"
COMMAND_PLUGIN = ROOT / "sideband" / "rns_filesync_command.py"


class SidebandPlugin:
    pass


class SidebandServicePlugin(SidebandPlugin):
    def __init__(self, sideband_core):
        self.__sideband = sideband_core
        self.__started = False
        self.service_name = type(self).service_name

    def start(self):
        self.__started = True

    def stop(self):
        self.__started = False

    def is_running(self):
        return self.__started is True

    def get_sideband(self):
        return self.__sideband


class SidebandCommandPlugin(SidebandPlugin):
    def __init__(self, sideband_core):
        self.__sideband = sideband_core
        self.__started = False
        self.command_name = type(self).command_name

    def start(self):
        self.__started = True

    def stop(self):
        self.__started = False

    def is_running(self):
        return self.__started is True

    def get_sideband(self):
        return self.__sideband

    def handle_command(self, arguments):
        raise NotImplementedError


def _load_plugin(path: Path):
    plugin_globals = {
        "SidebandServicePlugin": SidebandServicePlugin,
        "SidebandCommandPlugin": SidebandCommandPlugin,
    }
    exec(path.read_text(encoding="utf-8"), plugin_globals)
    return plugin_globals["plugin_class"]


def test_sideband_plugin_files_exist():
    assert SERVICE_PLUGIN.is_file()
    assert COMMAND_PLUGIN.is_file()


def test_sideband_service_plugin_loads_like_sideband():
    cls = _load_plugin(SERVICE_PLUGIN)
    assert cls.service_name == "rns_filesync"
    core = SimpleNamespace(
        identity=None,
        reticulum=None,
        app_dir="/tmp",
        active_service_plugins={},
    )
    plugin = cls(core)
    assert plugin.service_name == "rns_filesync"
    assert plugin.get_filesync() is None


def test_sideband_command_plugin_loads_like_sideband():
    cls = _load_plugin(COMMAND_PLUGIN)
    assert cls.command_name == "filesync"
    replies = []

    class FakeCore:
        active_service_plugins = {}

        def send_message(self, text, destination, *args, **kwargs):
            replies.append((text, destination))

    plugin = cls(FakeCore())
    plugin.start()
    assert plugin.is_running()
    plugin.handle_command([], SimpleNamespace(source_hash=b"\x01" * 16))
    assert replies
    assert "Usage" in replies[0][0]
    plugin.stop()
