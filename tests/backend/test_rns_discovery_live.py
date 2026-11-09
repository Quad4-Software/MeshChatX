# SPDX-License-Identifier: 0BSD

"""Tests for hot-applied Reticulum discovery settings (no stack reload)."""

import pytest
import RNS

from meshchatx.src.backend import rns_discovery_live as live


@pytest.fixture
def saved_rns_state():
    cls = RNS.Reticulum
    names = (
        "discover_interfaces",
        "interface_sources",
        "required_discovery_value",
        "autoconnect_discovered_interfaces",
        "autoconnect_unverified",
        "autoconnect_interface_mode",
        "autoconnect_interface_gravity",
        "autoconnect_announces_to_internal",
        "default_gravity",
    )
    saved = {n: getattr(cls, f"_Reticulum__{n}", None) for n in names}
    discovery_handler = getattr(RNS.Transport, "discovery_handler", None)
    yield
    for n, value in saved.items():
        setattr(cls, f"_Reticulum__{n}", value)
    try:
        RNS.Transport.discovery_handler = discovery_handler
    except Exception:
        pass


class _FakeApp:
    def __init__(self, reticulum_config, reticulum=None):
        self._config = reticulum_config
        self.reticulum = reticulum if reticulum is not None else object()

    def _get_reticulum_section(self):
        return self._config


def _class(name):
    return getattr(RNS.Reticulum, f"_Reticulum__{name}")


def test_live_apply_sets_dynamic_options(saved_rns_state, monkeypatch):
    monkeypatch.setattr(RNS.Transport, "discovery_handler", object())
    app = _FakeApp(
        {
            "discover_interfaces": "true",
            "interface_discovery_sources": "aa" * 16 + "," + "bb" * 16,
            "required_discovery_value": "16",
            "autoconnect_discovered_interfaces": "4",
            "autoconnect_unverified_implementations": "true",
            "autoconnect_interface_mode": "gateway",
            "autoconnect_interface_gravity": "-2",
            "autoconnect_announces_to_internal": "yes",
            "default_gravity": "5",
        }
    )
    applied, reason = live.apply_discovery_settings_live(app)
    assert applied is True
    assert reason is None
    assert _class("discover_interfaces") is True
    sources = _class("interface_sources")
    assert sources == [bytes.fromhex("aa" * 16), bytes.fromhex("bb" * 16)]
    assert _class("required_discovery_value") == 16.0
    assert _class("autoconnect_discovered_interfaces") == 4
    assert _class("autoconnect_unverified") is True
    assert _class("autoconnect_interface_gravity") == -2
    assert _class("autoconnect_announces_to_internal") is True
    assert _class("default_gravity") == 5


def test_live_apply_mode_maps_to_interface_constant(saved_rns_state):
    from RNS.Interfaces import Interface

    app = _FakeApp({"autoconnect_interface_mode": "access_point"})
    applied, _reason = live.apply_discovery_settings_live(app)
    assert applied is True
    assert (
        _class("autoconnect_interface_mode")
        == Interface.Interface.MODE_ACCESS_POINT
    )


def test_live_apply_unset_autoconnect_becomes_false(saved_rns_state):
    app = _FakeApp({})
    applied, _ = live.apply_discovery_settings_live(app)
    assert applied is True
    assert _class("autoconnect_discovered_interfaces") is False
    assert _class("discover_interfaces") is False
    assert _class("interface_sources") == []


def test_live_apply_invalid_sources_skipped(saved_rns_state):
    app = _FakeApp(
        {"interface_discovery_sources": "not-hex,zz" + "," + "cc" * 16}
    )
    applied, _ = live.apply_discovery_settings_live(app)
    assert applied is True
    assert _class("interface_sources") == [bytes.fromhex("cc" * 16)]


def test_live_apply_shared_instance_needs_reload(saved_rns_state):
    class _Shared:
        is_connected_to_shared_instance = True

    app = _FakeApp({}, reticulum=_Shared())
    applied, reason = live.apply_discovery_settings_live(app)
    assert applied is False
    assert reason == "shared-instance"


def test_live_apply_missing_reticulum_needs_reload(saved_rns_state):
    app = _FakeApp({})
    app.reticulum = None
    applied, reason = live.apply_discovery_settings_live(app)
    assert applied is False
    assert reason == "reticulum-unavailable"


def test_discovery_enable_creates_handler(saved_rns_state, monkeypatch):
    calls = []

    def fake_discover():
        calls.append(1)
        RNS.Transport.discovery_handler = object()

    monkeypatch.setattr(RNS.Transport, "discover_interfaces", fake_discover)
    monkeypatch.setattr(RNS.Transport, "discovery_handler", None)
    app = _FakeApp({"discover_interfaces": "true"})
    applied, reason = live.apply_discovery_settings_live(app)
    assert applied is True
    assert reason is None
    assert calls == [1]
    assert _class("discover_interfaces") is True


def test_discovery_disable_pauses_handler(saved_rns_state, monkeypatch):
    class _Announce:
        def __init__(self):
            self.paused = False

    class _Discovery:
        def __init__(self):
            self.handler = _Announce()
            self.monitoring_autoconnects = True
            self.monitored_interfaces = []

    discovery = _Discovery()
    monkeypatch.setattr(RNS.Transport, "discovery_handler", discovery)
    app = _FakeApp({"discover_interfaces": "false"})
    applied, reason = live.apply_discovery_settings_live(app)
    assert applied is True
    assert reason is None
    assert discovery.handler.paused is True
    assert discovery.monitoring_autoconnects is False


def test_discovery_enable_unpauses_existing(saved_rns_state, monkeypatch):
    class _Announce:
        def __init__(self):
            self.paused = True

    class _Discovery:
        def __init__(self):
            self.handler = _Announce()
            self.monitoring_autoconnects = True
            self.monitored_interfaces = []

    discovery = _Discovery()
    monkeypatch.setattr(RNS.Transport, "discovery_handler", discovery)
    app = _FakeApp({"discover_interfaces": "true"})
    applied, reason = live.apply_discovery_settings_live(app)
    assert applied is True
    assert reason is None
    assert discovery.handler.paused is False
