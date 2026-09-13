# SPDX-License-Identifier: 0BSD

"""Tests for the non-epoll BackboneClientInterface degradation.

Pins the issue-100 regression: on platforms without select.epoll (macOS,
Windows), RNS's BackboneClientInterface registers into a shared epoll loop
that does not exist, so every backbone client connection fails with
"module 'select' has no attribute 'epoll'" and retries forever. This broke
both manual type=BackboneInterface client configs and interface discovery
autoconnect on macOS.

The patch rebinds BackboneInterface.BackboneClientInterface to
TCPClientInterface, which speaks identical HDLC framing over TCP and is
what upstream's generated config entries already recommend on
non-Linux systems.
"""

import socket
from unittest.mock import MagicMock

import pytest

from meshchatx.src.backend import rns_backbone_patch


@pytest.fixture
def backbone_module():
    from RNS.Interfaces import BackboneInterface as module

    original = module.BackboneClientInterface
    yield module
    module.BackboneClientInterface = original


def _install_no_epoll(monkeypatch):
    monkeypatch.setattr(rns_backbone_patch, "_PATCHED", False)
    monkeypatch.setattr(rns_backbone_patch, "_epoll_supported", lambda: False)
    return rns_backbone_patch.install_rns_backbone_patches()


def test_install_noops_when_epoll_supported(monkeypatch, backbone_module):
    original = backbone_module.BackboneClientInterface
    monkeypatch.setattr(rns_backbone_patch, "_PATCHED", False)
    monkeypatch.setattr(rns_backbone_patch, "_epoll_supported", lambda: True)

    assert rns_backbone_patch.install_rns_backbone_patches() is False
    assert backbone_module.BackboneClientInterface is original


def test_install_degrades_client_without_epoll(monkeypatch, backbone_module):
    from RNS.Interfaces import TCPInterface

    assert _install_no_epoll(monkeypatch) is True
    assert backbone_module.BackboneClientInterface is TCPInterface.TCPClientInterface


def test_install_idempotent(monkeypatch, backbone_module):
    assert _install_no_epoll(monkeypatch) is True
    original_degraded = backbone_module.BackboneClientInterface
    assert rns_backbone_patch.install_rns_backbone_patches() is True
    assert backbone_module.BackboneClientInterface is original_degraded


def test_degraded_client_constructs_tcp_interface(monkeypatch, backbone_module):
    """A BackboneClientInterface() call yields a working TCPClientInterface.

    Passing connected_socket exercises the construction path without
    opening a real network connection.
    """
    assert _install_no_epoll(monkeypatch) is True
    _stub_autoconnect_env(monkeypatch)

    fake_socket = MagicMock()
    fake_socket.family = socket.AF_INET
    interface = backbone_module.BackboneClientInterface(
        MagicMock(),
        {"name": "Degraded backbone client"},
        connected_socket=fake_socket,
    )

    assert type(interface).__name__ == "TCPClientInterface"


def test_degraded_client_connects_to_real_tcp_listener(
    monkeypatch,
    backbone_module,
):
    """The degraded client must reach online against a real TCP listener.

    This is the socket-level path that died on macOS: upstream registered
    the fresh socket into epoll immediately after connect, so the
    connection was torn down and retried forever.
    """
    import time

    assert _install_no_epoll(monkeypatch) is True
    _stub_autoconnect_env(monkeypatch)

    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    port = listener.getsockname()[1]

    interface = backbone_module.BackboneClientInterface(
        MagicMock(),
        {"name": "t", "target_host": "127.0.0.1", "target_port": port},
    )
    try:
        deadline = time.time() + 5
        while not interface.online and time.time() < deadline:
            time.sleep(0.05)
        assert interface.online is True
    finally:
        interface.detach()
        listener.close()


def _stub_autoconnect_env(monkeypatch):
    """Stub the Reticulum/Transport state autoconnect reads."""
    import RNS

    added = []
    fake_instance = MagicMock()
    fake_instance._add_interface = lambda interface, **kwargs: added.append(
        (interface, kwargs),
    )

    monkeypatch.setattr(
        RNS.Reticulum,
        "should_autoconnect_discovered_interfaces",
        staticmethod(lambda: True),
    )
    monkeypatch.setattr(
        RNS.Reticulum,
        "max_autoconnected_interfaces",
        staticmethod(lambda: 3),
    )
    monkeypatch.setattr(
        RNS.Reticulum,
        "autoconnect_interface_mode",
        staticmethod(lambda: None),
    )
    monkeypatch.setattr(
        RNS.Reticulum,
        "autoconnect_announces_to_internal",
        staticmethod(lambda: None),
    )
    monkeypatch.setattr(
        RNS.Reticulum,
        "autoconnect_interface_gravity",
        staticmethod(lambda: None),
    )
    monkeypatch.setattr(
        RNS.Reticulum,
        "transport_enabled",
        staticmethod(lambda: False),
    )
    monkeypatch.setattr(
        RNS.Reticulum,
        "get_instance",
        staticmethod(lambda: fake_instance),
    )
    monkeypatch.setattr(RNS.Transport, "interfaces", [])

    return added


def _discovery_instance():
    from RNS.Discovery import InterfaceDiscovery

    discovery = InterfaceDiscovery.__new__(InterfaceDiscovery)
    discovery.monitored_interfaces = []
    discovery.monitoring_autoconnects = True
    return discovery


def test_autoconnect_builds_tcp_client_without_epoll(
    monkeypatch,
    backbone_module,
):
    """A discovered BackboneInterface must autoconnect via TCPClientInterface."""
    assert _install_no_epoll(monkeypatch) is True
    added = _stub_autoconnect_env(monkeypatch)

    from RNS.Interfaces import TCPInterface

    monkeypatch.setattr(
        TCPInterface.TCPClientInterface,
        "initial_connect",
        lambda self: None,
    )

    discovery = _discovery_instance()
    info = {
        "type": "BackboneInterface",
        "name": "AT-Vienna-Backbone",
        "reachable_on": "85.10.200.4",
        "port": 4242,
        "network_id": "aa" * 16,
        "transport_id": "bb" * 16,
        "config_entry": "",
    }

    discovery.autoconnect(info)

    assert len(added) == 1
    interface, _kwargs = added[0]
    assert type(interface).__name__ == "TCPClientInterface"
    assert interface.target_ip == "85.10.200.4"
    assert interface.target_port == 4242
    assert interface.autoconnect_hash == discovery.endpoint_hash(info)
    assert interface in discovery.monitored_interfaces


def test_degraded_interface_dedup_via_interface_exists(
    monkeypatch,
    backbone_module,
):
    """A degraded interface must dedup against later discovered announces.

    Without target_ip/target_port matching, the monitor job would keep
    spawning duplicate autoconnects for the same endpoint.
    """
    import RNS

    assert _install_no_epoll(monkeypatch) is True
    _stub_autoconnect_env(monkeypatch)

    from RNS.Interfaces import TCPInterface

    monkeypatch.setattr(
        TCPInterface.TCPClientInterface,
        "initial_connect",
        lambda self: None,
    )

    discovery = _discovery_instance()
    info = {
        "type": "BackboneInterface",
        "name": "AT-Vienna-Backbone",
        "reachable_on": "85.10.200.4",
        "port": 4242,
        "network_id": "aa" * 16,
        "transport_id": "bb" * 16,
        "config_entry": "",
    }
    discovery.autoconnect(info)
    RNS.Transport.interfaces.append(discovery.monitored_interfaces[0])

    assert discovery.interface_exists(info) is True
    discovery.autoconnect(info)
    assert len(discovery.monitored_interfaces) == 1
