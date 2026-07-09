# SPDX-License-Identifier: 0BSD

import shutil
from pathlib import Path

import RNS

from meshchatx.src.backend.plugin_rsg import create_rsg
from meshchatx.src.backend.sideband_plugin_loader import SidebandPluginLoader

SIDEBAND_FIXTURES = (
    Path(__file__).resolve().parent / "fixtures" / "sideband_plugins"
)


class FakeConfigValue:
    def __init__(self, value):
        self._value = value

    def get(self):
        return self._value

    def set(self, value):
        self._value = value


class FakeConfig:
    def __init__(self):
        self.service_plugins_enabled = FakeConfigValue(False)
        self.command_plugins_enabled = FakeConfigValue(False)
        self.command_plugins_path = FakeConfigValue(None)
        self.telemetry_enabled = FakeConfigValue(False)


class FakeApp:
    def __init__(self):
        self.config = FakeConfig()
        self.sent = []

    def send_message(self, content, destination_hash, propagation, **kwargs):
        self.sent.append((content, destination_hash, propagation, kwargs))
        return True


COMMAND_PLUGIN = """
class DemoCommand(SidebandCommandPlugin):
    command_name = "demo"

    def handle_command(self, arguments, message=None):
        self.get_sideband().send_message("ok:" + ",".join(arguments), b"abcd", False)

plugin_class = DemoCommand
"""


class FakeLxm:
    def __init__(self, source_hash: bytes):
        self.source_hash = source_hash


def _enable_sideband_plugins(app, plugins_path):
    app.config.service_plugins_enabled.set(True)
    app.config.command_plugins_enabled.set(True)
    app.config.command_plugins_path.set(str(plugins_path))
    app.config.telemetry_enabled.set(True)


def _copy_fixture(tmp_path, name: str) -> Path:
    plugins = tmp_path / "plugins"
    plugins.mkdir()
    shutil.copy(SIDEBAND_FIXTURES / name, plugins / name)
    return plugins


def test_load_gates_and_command_dispatch(tmp_path):
    plugins = tmp_path / "plugins"
    plugins.mkdir()
    script = plugins / "demo.py"
    script.write_text(COMMAND_PLUGIN, encoding="utf-8")

    app = FakeApp()
    loader = SidebandPluginLoader(app)
    result = loader.reload()
    assert result["loaded"] == 0

    app.config.service_plugins_enabled.set(True)
    app.config.command_plugins_enabled.set(True)
    app.config.command_plugins_path.set(str(plugins))
    result = loader.reload()
    assert result["loaded"] == 1
    assert loader.handle_plugin_command("demo one two", object()) is True
    assert app.sent[0][0] == "ok:one,two"


def test_optional_py_rsg_blocks_invalid(tmp_path):
    plugins = tmp_path / "plugins"
    plugins.mkdir()
    script = plugins / "demo.py"
    source = COMMAND_PLUGIN.encode("utf-8")
    script.write_bytes(source)
    (plugins / "demo.py.rsg").write_bytes(b"z" * 80)

    app = FakeApp()
    app.config.service_plugins_enabled.set(True)
    app.config.command_plugins_enabled.set(True)
    app.config.command_plugins_path.set(str(plugins))
    loader = SidebandPluginLoader(app)
    result = loader.reload()
    assert result["loaded"] == 0
    assert result["plugins"][0]["error"]

    identity = RNS.Identity()
    (plugins / "demo.py.rsg").write_bytes(create_rsg(source, identity))
    result = loader.reload()
    assert result["loaded"] == 1
    assert result["plugins"][0]["signature"]["valid"] is True


def test_load_real_basic_command_plugin(tmp_path):
    plugins = _copy_fixture(tmp_path, "basic.py")
    app = FakeApp()
    _enable_sideband_plugins(app, plugins)
    loader = SidebandPluginLoader(app)
    result = loader.reload()
    assert result["loaded"] == 1
    command_plugins = [
        item for item in result["plugins"] if item.get("type") == "command"
    ]
    assert len(command_plugins) == 1
    assert command_plugins[0]["plugin_name"] == "basic_example"
    assert "basic_example" in loader.active_command_plugins


def test_real_basic_command_dispatch(tmp_path):
    plugins = _copy_fixture(tmp_path, "basic.py")
    app = FakeApp()
    _enable_sideband_plugins(app, plugins)
    loader = SidebandPluginLoader(app)
    loader.reload()
    source_hash = b"\xab\xcd\xef\x01"
    lxm = FakeLxm(source_hash)
    assert loader.handle_plugin_command("basic_example alpha beta", lxm) is True
    assert len(app.sent) == 1
    content, destination, propagation, kwargs = app.sent[0]
    assert destination == source_hash
    assert propagation is False
    assert kwargs.get("skip_fields") is True
    assert kwargs.get("no_display") is True
    assert RNS.prettyhexrep(source_hash) in content
    assert "alpha" in content
    assert "beta" in content


def test_load_real_telemetry_plugin(tmp_path):
    plugins = _copy_fixture(tmp_path, "telemetry.py")
    app = FakeApp()
    _enable_sideband_plugins(app, plugins)
    loader = SidebandPluginLoader(app)
    result = loader.reload()
    assert result["loaded"] == 1
    telemetry_plugins = [
        item for item in result["plugins"] if item.get("type") == "telemetry"
    ]
    assert len(telemetry_plugins) == 1
    assert telemetry_plugins[0]["plugin_name"] == "telemetry_example"
    telemetry = loader.update_telemetry()
    assert "power_consumption" in telemetry
    assert "power_production" in telemetry
    assert "processor" in telemetry
    assert telemetry["processor"]["entries"]
