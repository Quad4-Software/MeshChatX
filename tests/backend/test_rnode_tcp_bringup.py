# SPDX-License-Identifier: 0BSD

"""End-to-end RNodeInterface bring-up against a KISS TCP simulator.

Covers detect, firmware/platform/MCU probes, radio config validation,
TX/RX data, reconnect after link loss, detect timeouts, the old-firmware
panic path, and bt:// port translation.
"""

import time

import pytest
import RNS

from meshchatx.src.backend.rns_rnode_patch import install_rns_rnode_patches
from meshchatx.src.backend.rns_startup_recovery import (
    install_rns_panic_containment,
)
from tests.backend.rnode_simulator import RNodeSimulator

_CONFIG = """\
[reticulum]
  enable_transport = No
  share_instance = No
  panic_on_interface_error = No

[interfaces]
  [[Simulated RNode]]
  type = RNodeInterface
  interface_enabled = yes
  port = tcp://127.0.0.1
  frequency = 867200000
  bandwidth = 125000
  txpower = 7
  spreadingfactor = 7
  codingrate = 5
"""


def _wait_for(predicate, timeout=15.0, interval=0.1):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return False


def _find_rnode():
    from RNS.Interfaces import RNodeInterface as rnode_module

    return [
        i
        for i in RNS.Transport.interfaces
        if isinstance(i, rnode_module.RNodeInterface)
    ]


def _teardown_reticulum():
    """Fully reset RNS singletons so each test gets a fresh Reticulum."""
    try:
        RNS.Reticulum.exit_handler()
    except Exception:
        pass
    if hasattr(RNS.Reticulum, "_Reticulum__instance"):
        RNS.Reticulum._Reticulum__instance = None
    for flag in (
        "_Reticulum__exit_handler_ran",
        "_Reticulum__interface_detach_ran",
    ):
        if hasattr(RNS.Reticulum, flag):
            setattr(RNS.Reticulum, flag, False)
    try:
        from meshchatx.meshchat import ReticulumMeshChat

        ReticulumMeshChat._reset_transport_globals_for_reload()
    except Exception:
        RNS.Transport._should_run = True
        RNS.Transport.interfaces = []


@pytest.fixture()
def sim():
    simulator = RNodeSimulator().start()
    yield simulator
    simulator.stop()


@pytest.fixture()
def reticulum(tmp_path, monkeypatch, sim):
    """Boot a real Reticulum with an RNode TCP interface at the simulator."""
    install_rns_panic_containment()
    install_rns_rnode_patches()

    from RNS.Interfaces import RNodeInterface as rnode_module

    monkeypatch.setattr(
        rnode_module.TCPConnection, "TARGET_PORT", sim.port, raising=True
    )
    (tmp_path / "config").write_text(_CONFIG, encoding="utf-8")
    rns = RNS.Reticulum(configdir=str(tmp_path), loglevel=RNS.LOG_ERROR)
    yield rns
    _teardown_reticulum()


def test_rnode_tcp_bringup_detect_configure_and_exchange(reticulum, sim):
    rnodes = _find_rnode()
    assert len(rnodes) == 1
    iface = rnodes[0]

    assert _wait_for(lambda: iface.online, timeout=20), (
        "interface never came online against the simulator"
    )
    assert iface.detected is True
    assert iface.firmware_ok is True
    assert iface.maj_version == 1 and iface.min_version == 60
    assert iface.platform == 0x80

    # The simulator echoed every config write back and validation passed.
    assert sim.config.get("frequency") == 867200000
    assert sim.config.get("bandwidth") == 125000
    assert sim.config.get("txpower") == 7
    assert sim.config.get("spreadingfactor") == 7
    assert sim.radio_state == 1
    assert iface.r_frequency == 867200000

    # Outbound frames reach the device (announce traffic may interleave).
    iface.process_outgoing(b"hello-mesh-rnode")
    assert _wait_for(lambda: b"hello-mesh-rnode" in sim.received_data, timeout=10), (
        "simulator never saw the outbound frame"
    )

    # Inbound frames reach Transport; rxb proves delivery to the interface.
    before = iface.rxb
    assert sim.inject_data(b"uplink-payload")
    assert _wait_for(lambda: iface.rxb > before, timeout=10)


def test_rnode_tcp_reconnects_after_link_loss(reticulum, sim):
    iface = _find_rnode()[0]
    assert _wait_for(lambda: iface.online, timeout=20)

    sim.stop()
    assert _wait_for(lambda: not iface.online, timeout=15), (
        "interface never noticed the dropped link"
    )

    sim.start()
    assert _wait_for(lambda: iface.online, timeout=40), (
        "interface did not reconnect after the simulator came back"
    )
    assert iface.detected is True


def test_rnode_tcp_detect_timeout_stays_offline(tmp_path, monkeypatch):
    install_rns_panic_containment()
    install_rns_rnode_patches()

    silent = RNodeSimulator(respond_to_detect=False).start()
    try:
        from RNS.Interfaces import RNodeInterface as rnode_module

        monkeypatch.setattr(
            rnode_module.TCPConnection,
            "TARGET_PORT",
            silent.port,
            raising=True,
        )
        (tmp_path / "config").write_text(_CONFIG, encoding="utf-8")
        rns = RNS.Reticulum(configdir=str(tmp_path), loglevel=RNS.LOG_ERROR)
        try:
            # The device never answers detect: the interface must stay
            # offline and retry forever without taking Reticulum down. The
            # reconnect loop keeps cycling detect attempts, so assert the
            # stable invariant instead: never online, instance alive.
            iface = _find_rnode()[0]
            time.sleep(9)
            assert iface.online is False
            assert iface.detected is False
            assert RNS.Reticulum.get_instance() is rns
        finally:
            _teardown_reticulum()
    finally:
        silent.stop()


def test_rnode_old_firmware_panics_are_contained(tmp_path, monkeypatch):
    """Old firmware must not kill the process.

    An RNode reporting too-old firmware calls RNS.panic from the read
    thread; panic containment must turn that into a survivable condition
    instead of os._exit killing the whole process.
    """
    install_rns_panic_containment()
    install_rns_rnode_patches()

    old_fw = RNodeSimulator(fw_version=(1, 20)).start()
    try:
        from RNS.Interfaces import RNodeInterface as rnode_module

        monkeypatch.setattr(
            rnode_module.TCPConnection,
            "TARGET_PORT",
            old_fw.port,
            raising=True,
        )
        (tmp_path / "config").write_text(_CONFIG, encoding="utf-8")
        RNS.Reticulum(configdir=str(tmp_path), loglevel=RNS.LOG_ERROR)
        try:
            iface = _find_rnode()[0]
            # Wait past the detect+validate window; process is still here.
            time.sleep(8)
            assert iface.online is False or iface.firmware_ok is False
        finally:
            _teardown_reticulum()
    finally:
        old_fw.stop()


def test_rnode_bt_port_translates_to_serial_target(tmp_path, monkeypatch):
    """bt:// targets resolve through bt_serial_ports before RNS opens them."""
    import os
    import pty

    install_rns_panic_containment()
    install_rns_rnode_patches()

    master, slave = pty.openpty()
    slave_name = os.ttyname(slave)
    try:
        monkeypatch.setattr(
            "meshchatx.src.backend.bt_serial_ports.resolve_bt_target",
            lambda target, ports=None: slave_name,
        )
        config = _CONFIG.replace("port = tcp://127.0.0.1", "port = bt://MyRNode")
        (tmp_path / "config").write_text(config, encoding="utf-8")
        RNS.Reticulum(configdir=str(tmp_path), loglevel=RNS.LOG_ERROR)
        try:
            iface = _find_rnode()[0]
            # The interface opened the resolved serial device, not the
            # bt:// URI. The pty never answers detect, so it stays offline.
            assert iface.port == slave_name
            assert iface.use_ble is False and iface.use_tcp is False
        finally:
            _teardown_reticulum()
    finally:
        os.close(master)
        os.close(slave)


def test_rnode_bt_unresolvable_retries_without_panic(tmp_path, monkeypatch):
    """An unpaired bt:// target must retry instead of killing startup.

    Resolution is lazy: every open_port attempt re-resolves, so the
    interface comes up on its own once the OS exposes the serial port.
    """
    import os
    import pty

    install_rns_panic_containment()
    install_rns_rnode_patches()

    master, slave = pty.openpty()
    slave_name = os.ttyname(slave)
    calls = []

    def _resolver(target, ports=None):
        calls.append(target)
        if len(calls) < 3:
            raise OSError("no Bluetooth serial ports found")
        return slave_name

    try:
        monkeypatch.setattr(
            "meshchatx.src.backend.bt_serial_ports.resolve_bt_target",
            _resolver,
        )
        config = _CONFIG.replace("port = tcp://127.0.0.1", "port = bt://MyRNode")
        (tmp_path / "config").write_text(config, encoding="utf-8")
        RNS.Reticulum(configdir=str(tmp_path), loglevel=RNS.LOG_ERROR)
        try:
            iface = _find_rnode()[0]
            # The reconnect loop must keep retrying the failed resolution
            # until it succeeds, without RNS.panic killing the process.
            assert _wait_for(lambda: iface.port == slave_name, timeout=30.0)
            assert len(calls) >= 3
            assert RNS.Reticulum._Reticulum__instance is not None
        finally:
            _teardown_reticulum()
    finally:
        os.close(master)
        os.close(slave)
