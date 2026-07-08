# SPDX-License-Identifier: 0BSD

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from meshchatx.src.backend import rnode_support


def test_normalize_rnode_tcp_host_backfills_from_port(tmp_path):
    """RNS's Android RNodeInterface reads tcp_host as its own config key.

    Configs written with only ``port = tcp://host:port`` (which is all the
    desktop RNodeInterface needs) silently try to open the RNode as a serial
    device on Android unless tcp_host is also present.
    """
    config_path = tmp_path / "config"
    config_path.write_text(
        """[interfaces]
    [[RNode TCP]]
    type = RNodeInterface
    interface_enabled = True
    port = tcp://192.0.2.1:4242
""",
        encoding="utf-8",
    )

    assert rnode_support.normalize_rnode_tcp_host_in_config(str(config_path)) is True
    text = config_path.read_text(encoding="utf-8")
    assert "tcp_host = 192.0.2.1:4242" in text


def test_normalize_rnode_tcp_host_leaves_non_tcp_entries_alone(tmp_path):
    config_path = tmp_path / "config"
    config_path.write_text(
        """[interfaces]
    [[RNode Serial]]
    type = RNodeInterface
    interface_enabled = True
    port = /dev/ttyUSB0
""",
        encoding="utf-8",
    )

    assert rnode_support.normalize_rnode_tcp_host_in_config(str(config_path)) is False
    assert "tcp_host" not in config_path.read_text(encoding="utf-8")


def test_normalize_rnode_tcp_host_is_idempotent(tmp_path):
    config_path = tmp_path / "config"
    config_path.write_text(
        """[interfaces]
    [[RNode TCP]]
    type = RNodeInterface
    interface_enabled = True
    port = tcp://192.0.2.1:4242
    tcp_host = 192.0.2.1:4242
""",
        encoding="utf-8",
    )

    assert rnode_support.normalize_rnode_tcp_host_in_config(str(config_path)) is False


@pytest.mark.parametrize(
    ("port", "expected"),
    [
        ("tcp://192.0.2.1:4242", "192.0.2.1:4242"),
        ("tcp://mesh.example", "mesh.example"),
        ("tcp://mesh.example:", "mesh.example"),
        ("tcp://", None),
        ("tcp:///", None),
        ("/dev/ttyUSB0", None),
    ],
)
def test_tcp_host_from_port(port, expected):
    assert rnode_support._tcp_host_from_port(port) == expected


def test_normalize_rnode_tcp_host_handles_port_variants(tmp_path):
    config_path = tmp_path / "config"
    config_path.write_text(
        """[interfaces]
[[RNode TCP]]
type = RNodeInterface
interface_enabled = True
port =   TCP://mesh.example:4242
""",
        encoding="utf-8",
    )

    assert rnode_support.normalize_rnode_tcp_host_in_config(str(config_path)) is True
    assert "tcp_host = mesh.example:4242" in config_path.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "port",
    ["tcp://", "  tcp://  ", "tcp:///"],
)
def test_normalize_rnode_tcp_host_skips_empty_host(tmp_path, port):
    config_path = tmp_path / "config"
    config_path.write_text(
        f"""[interfaces]
[[RNode TCP]]
type = RNodeInterface
interface_enabled = True
port = {port}
""",
        encoding="utf-8",
    )

    assert rnode_support.normalize_rnode_tcp_host_in_config(str(config_path)) is False
    assert "tcp_host" not in config_path.read_text(encoding="utf-8")


def test_normalize_rnode_tcp_host_updates_mismatched_tcp_host(tmp_path):
    config_path = tmp_path / "config"
    config_path.write_text(
        """[interfaces]
[[RNode TCP]]
type = RNodeInterface
interface_enabled = True
port = tcp://192.0.2.1:4242
tcp_host = stale.example:1
""",
        encoding="utf-8",
    )

    assert rnode_support.normalize_rnode_tcp_host_in_config(str(config_path)) is True
    assert "tcp_host = 192.0.2.1:4242" in config_path.read_text(encoding="utf-8")


def test_normalize_rnode_tcp_host_missing_file_returns_false(tmp_path):
    assert (
        rnode_support.normalize_rnode_tcp_host_in_config(str(tmp_path / "missing"))
        is False
    )


def test_normalize_rnode_tcp_host_invalid_config_returns_false(tmp_path):
    config_path = tmp_path / "config"
    config_path.write_text("not valid configobj syntax [[[", encoding="utf-8")
    assert rnode_support.normalize_rnode_tcp_host_in_config(str(config_path)) is False


def test_guard_disables_rnode_when_usbserial4a_missing(tmp_path, monkeypatch):
    config_path = tmp_path / "config"
    config_path.write_text(
        """[interfaces]
    [[RNode Serial]]
    type = RNodeInterface
    interface_enabled = True
    port = /dev/ttyUSB0
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(rnode_support, "_is_chaquopy_android", lambda: True)
    monkeypatch.setattr(rnode_support, "android_usbserial4a_available", lambda: False)
    monkeypatch.setattr(rnode_support, "android_jnius_available", lambda: False)

    assert rnode_support.guard_rnode_interfaces_on_android(str(config_path)) is True
    assert "interface_enabled = false" in config_path.read_text(encoding="utf-8")


def test_guard_disables_rnode_when_jnius_missing(tmp_path, monkeypatch):
    """usbserial4a alone is not enough for serial/classic-Bluetooth ports.

    RNS's Android RNodeInterface also needs jnius for those transports.
    """
    config_path = tmp_path / "config"
    config_path.write_text(
        """[interfaces]
    [[RNode Serial]]
    type = RNodeInterface
    interface_enabled = True
    port = /dev/ttyUSB0
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(rnode_support, "_is_chaquopy_android", lambda: True)
    monkeypatch.setattr(rnode_support, "android_usbserial4a_available", lambda: True)
    monkeypatch.setattr(rnode_support, "android_jnius_available", lambda: False)

    assert rnode_support.guard_rnode_interfaces_on_android(str(config_path)) is True
    assert "interface_enabled = false" in config_path.read_text(encoding="utf-8")


def test_guard_keeps_rnode_when_usbserial4a_and_jnius_available(tmp_path, monkeypatch):
    config_path = tmp_path / "config"
    config_path.write_text(
        """[interfaces]
    [[RNode Serial]]
    type = RNodeInterface
    interface_enabled = True
    port = /dev/ttyUSB0
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(rnode_support, "_is_chaquopy_android", lambda: True)
    monkeypatch.setattr(rnode_support, "android_usbserial4a_available", lambda: True)
    monkeypatch.setattr(rnode_support, "android_jnius_available", lambda: True)

    assert rnode_support.guard_rnode_interfaces_on_android(str(config_path)) is False
    assert "interface_enabled = True" in config_path.read_text(encoding="utf-8")


def test_guard_keeps_tcp_rnode_enabled_even_without_usbserial4a_or_jnius(
    tmp_path,
    monkeypatch,
):
    """RNode over TCP needs no native Android modules and must stay enabled."""
    config_path = tmp_path / "config"
    config_path.write_text(
        """[interfaces]
    [[RNode TCP]]
    type = RNodeInterface
    interface_enabled = True
    port = tcp://192.0.2.1:4242
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(rnode_support, "_is_chaquopy_android", lambda: True)
    monkeypatch.setattr(rnode_support, "android_usbserial4a_available", lambda: False)
    monkeypatch.setattr(rnode_support, "android_jnius_available", lambda: False)

    assert rnode_support.guard_rnode_interfaces_on_android(str(config_path)) is False
    assert "interface_enabled = True" in config_path.read_text(encoding="utf-8")


def test_guard_disables_ble_rnode_when_able_missing(tmp_path, monkeypatch):
    config_path = tmp_path / "config"
    config_path.write_text(
        """[interfaces]
    [[RNode BLE]]
    type = RNodeInterface
    interface_enabled = True
    port = ble://aa:bb:cc:dd:ee:ff
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(rnode_support, "_is_chaquopy_android", lambda: True)
    monkeypatch.setattr(rnode_support, "android_able_available", lambda: False)

    assert rnode_support.guard_rnode_interfaces_on_android(str(config_path)) is True
    assert "interface_enabled = false" in config_path.read_text(encoding="utf-8")


def test_guard_keeps_ble_rnode_when_able_available(tmp_path, monkeypatch):
    config_path = tmp_path / "config"
    config_path.write_text(
        """[interfaces]
    [[RNode BLE]]
    type = RNodeInterface
    interface_enabled = True
    port = ble://aa:bb:cc:dd:ee:ff
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(rnode_support, "_is_chaquopy_android", lambda: True)
    monkeypatch.setattr(rnode_support, "android_able_available", lambda: True)
    monkeypatch.setattr(rnode_support, "android_usbserial4a_available", lambda: True)
    monkeypatch.setattr(rnode_support, "android_jnius_available", lambda: True)

    assert rnode_support.guard_rnode_interfaces_on_android(str(config_path)) is False
    assert "interface_enabled = True" in config_path.read_text(encoding="utf-8")


def test_guard_always_disables_rnode_multi_interface_on_android(tmp_path, monkeypatch):
    """RNS has no Android-specific RNodeMultiInterface; it always crashes there."""
    config_path = tmp_path / "config"
    config_path.write_text(
        """[interfaces]
    [[RNode Multi]]
    type = RNodeMultiInterface
    interface_enabled = True
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(rnode_support, "_is_chaquopy_android", lambda: True)
    monkeypatch.setattr(rnode_support, "android_usbserial4a_available", lambda: True)
    monkeypatch.setattr(rnode_support, "android_jnius_available", lambda: True)
    monkeypatch.setattr(rnode_support, "android_able_available", lambda: True)

    assert rnode_support.guard_rnode_interfaces_on_android(str(config_path)) is True
    assert "interface_enabled = false" in config_path.read_text(encoding="utf-8")


def test_guard_skips_rnode_multi_interface_off_android(tmp_path, monkeypatch):
    config_path = tmp_path / "config"
    config_path.write_text(
        """[interfaces]
    [[RNode Multi]]
    type = RNodeMultiInterface
    interface_enabled = True
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(rnode_support, "_is_chaquopy_android", lambda: False)

    assert rnode_support.guard_rnode_interfaces_on_android(str(config_path)) is False
    assert "interface_enabled = True" in config_path.read_text(encoding="utf-8")


def test_guard_rnode_interfaces_on_desktop_disables_ble_without_bleak(
    tmp_path,
    monkeypatch,
):
    config_path = tmp_path / "config"
    config_path.write_text(
        """[interfaces]
[[RNode BLE]]
type = RNodeInterface
interface_enabled = True
port = ble://aa:bb:cc:dd:ee:ff
[[RNode TCP]]
type = RNodeInterface
interface_enabled = True
port = tcp://192.0.2.1:4242
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(rnode_support, "_is_chaquopy_android", lambda: False)
    monkeypatch.setattr(rnode_support, "desktop_ble_stack_available", lambda: False)
    monkeypatch.setattr(rnode_support, "desktop_serial_stack_available", lambda: True)

    assert rnode_support.guard_rnode_interfaces_on_desktop(str(config_path)) is True
    text = config_path.read_text(encoding="utf-8").lower()
    assert text.count("interface_enabled = false") == 1


def test_guard_rnode_interfaces_on_desktop_skips_on_android(tmp_path, monkeypatch):
    config_path = tmp_path / "config"
    config_path.write_text(
        """[interfaces]
[[RNode BLE]]
type = RNodeInterface
interface_enabled = True
port = ble://aa:bb:cc:dd:ee:ff
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(rnode_support, "_is_chaquopy_android", lambda: True)
    monkeypatch.setattr(rnode_support, "desktop_ble_stack_available", lambda: False)

    assert rnode_support.guard_rnode_interfaces_on_desktop(str(config_path)) is False
    assert "interface_enabled = True" in config_path.read_text(encoding="utf-8")


def test_guard_skips_already_disabled_interfaces(tmp_path, monkeypatch):
    config_path = tmp_path / "config"
    config_path.write_text(
        """[interfaces]
[[RNode Serial]]
type = RNodeInterface
interface_enabled = false
port = /dev/ttyUSB0
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(rnode_support, "_is_chaquopy_android", lambda: True)
    monkeypatch.setattr(rnode_support, "android_usbserial4a_available", lambda: False)

    assert rnode_support.guard_rnode_interfaces_on_android(str(config_path)) is False


@pytest.mark.parametrize("enabled_key", ["interface_enabled", "enabled"])
def test_guard_honors_enabled_key_variants(tmp_path, monkeypatch, enabled_key):
    config_path = tmp_path / "config"
    config_path.write_text(
        f"""[interfaces]
[[RNode Serial]]
type = RNodeInterface
{enabled_key} = yes
port = /dev/ttyUSB0
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(rnode_support, "_is_chaquopy_android", lambda: True)
    monkeypatch.setattr(rnode_support, "android_usbserial4a_available", lambda: False)
    monkeypatch.setattr(rnode_support, "android_jnius_available", lambda: False)

    assert rnode_support.guard_rnode_interfaces_on_android(str(config_path)) is True
    assert "interface_enabled = false" in config_path.read_text(encoding="utf-8")


def test_rnode_serial_supported_on_desktop(monkeypatch):
    monkeypatch.setattr(rnode_support, "_is_chaquopy_android", lambda: False)
    assert rnode_support.rnode_serial_supported() is True


def test_rnode_serial_supported_on_android_requires_both_modules(monkeypatch):
    monkeypatch.setattr(rnode_support, "_is_chaquopy_android", lambda: True)
    monkeypatch.setattr(rnode_support, "android_usbserial4a_available", lambda: True)
    monkeypatch.setattr(rnode_support, "android_jnius_available", lambda: False)
    assert rnode_support.rnode_serial_supported() is False

    monkeypatch.setattr(rnode_support, "android_usbserial4a_available", lambda: False)
    monkeypatch.setattr(rnode_support, "android_jnius_available", lambda: True)
    assert rnode_support.rnode_serial_supported() is False

    monkeypatch.setattr(rnode_support, "android_usbserial4a_available", lambda: True)
    monkeypatch.setattr(rnode_support, "android_jnius_available", lambda: True)
    assert rnode_support.rnode_serial_supported() is True


def test_rnode_transport_supported_tcp_always_true_on_android(monkeypatch):
    monkeypatch.setattr(rnode_support, "_is_chaquopy_android", lambda: True)
    monkeypatch.setattr(rnode_support, "android_usbserial4a_available", lambda: False)
    monkeypatch.setattr(rnode_support, "android_jnius_available", lambda: False)
    monkeypatch.setattr(rnode_support, "android_able_available", lambda: False)

    assert (
        rnode_support.rnode_transport_supported({"port": "tcp://example.org:4242"})
        is True
    )


def test_rnode_transport_supported_tcp_always_true_on_desktop_without_pyserial(
    monkeypatch,
):
    monkeypatch.setattr(rnode_support, "desktop_serial_stack_available", lambda: False)

    assert (
        rnode_support.rnode_transport_supported(
            {"port": "tcp://example.org:4242"},
            is_android=False,
        )
        is True
    )


def test_rnode_transport_supported_serial_false_on_desktop_without_pyserial(
    monkeypatch,
):
    monkeypatch.setattr(rnode_support, "desktop_serial_stack_available", lambda: False)

    assert (
        rnode_support.rnode_transport_supported(
            {"port": "/dev/ttyUSB0"},
            is_android=False,
        )
        is False
    )


def test_rnode_transport_supported_bluetooth_classic_needs_usbserial_and_jnius(
    monkeypatch,
):
    monkeypatch.setattr(rnode_support, "_is_chaquopy_android", lambda: True)
    monkeypatch.setattr(rnode_support, "android_usbserial4a_available", lambda: True)
    monkeypatch.setattr(rnode_support, "android_jnius_available", lambda: True)

    iface = {"port": "", "allow_bluetooth": "true"}
    assert rnode_support.rnode_transport_supported(iface) is True

    monkeypatch.setattr(rnode_support, "android_jnius_available", lambda: False)
    assert rnode_support.rnode_transport_supported(iface) is False


def test_rnode_transport_supported_whitespace_port_with_bluetooth_classic(
    monkeypatch,
):
    monkeypatch.setattr(rnode_support, "_is_chaquopy_android", lambda: True)
    monkeypatch.setattr(rnode_support, "android_usbserial4a_available", lambda: True)
    monkeypatch.setattr(rnode_support, "android_jnius_available", lambda: True)

    iface = {"port": "   ", "allow_bluetooth": "yes"}
    assert rnode_support.rnode_transport_supported(iface) is True


@pytest.mark.parametrize(
    ("port", "is_tcp", "is_ble"),
    [
        ("tcp://host:1", True, False),
        ("TCP://HOST:1", True, False),
        ("  tcp://host  ", True, False),
        ("ble://aa:bb:cc:dd:ee:ff", False, True),
        ("BLE://AA:BB", False, True),
        ("/dev/ttyUSB0", False, False),
        (None, False, False),
        ("", False, False),
        ("   ", False, False),
        (123, False, False),
        ("serial://not-tcp", False, False),
    ],
)
def test_rnode_port_prefix_detection(port, is_tcp, is_ble):
    assert rnode_support.rnode_port_is_tcp(port) is is_tcp
    assert rnode_support.rnode_port_is_ble(port) is is_ble


@pytest.mark.parametrize(
    ("iface", "expected"),
    [
        ({"port": "tcp://host:1"}, "tcp"),
        ({"port": "ble://aa:bb"}, "ble"),
        ({"port": "", "allow_bluetooth": "true"}, "bluetooth_classic"),
        ({"port": "   ", "allow_bluetooth": "on"}, "bluetooth_classic"),
        ({"port": "/dev/ttyUSB0"}, "serial"),
        ({"port": "/dev/ttyUSB0", "allow_bluetooth": "true"}, "serial"),
    ],
)
def test_rnode_iface_transport_classification(iface, expected):
    assert rnode_support._rnode_iface_transport(iface) == expected


def test_disable_rnode_interfaces_on_desktop_disables_serial_without_pyserial(
    tmp_path,
    monkeypatch,
):
    config_path = tmp_path / "config"
    config_path.write_text(
        """[interfaces]
[[RNode Serial]]
type = RNodeInterface
interface_enabled = True
port = /dev/ttyUSB0
[[RNode TCP]]
type = RNodeInterface
interface_enabled = True
port = tcp://192.0.2.1:4242
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(rnode_support, "desktop_serial_stack_available", lambda: False)

    assert (
        rnode_support.disable_rnode_interfaces_in_config(
            str(config_path),
            is_android=False,
        )
        is True
    )
    text = config_path.read_text(encoding="utf-8").lower()
    assert "interface_enabled = false" in text
    assert text.count("interface_enabled = false") == 1


def test_guard_disables_rnode_with_invalid_txpower(tmp_path):
    config_path = tmp_path / "config"
    config_path.write_text(
        """[interfaces]
[[t9-srv]]
type = RNodeInterface
interface_enabled = True
port = /dev/ttyUSB0
frequency = 868000000
bandwidth = 125000
txpower = -9
spreadingfactor = 8
codingrate = 5
""",
        encoding="utf-8",
    )

    assert rnode_support.guard_invalid_rnode_txpower_in_config(str(config_path)) is True
    text = config_path.read_text(encoding="utf-8")
    assert "interface_enabled = false" in text.lower()


def test_guard_keeps_rnode_with_valid_txpower(tmp_path):
    config_path = tmp_path / "config"
    config_path.write_text(
        """[interfaces]
[[Radio]]
type = RNodeInterface
interface_enabled = True
txpower = 7
""",
        encoding="utf-8",
    )

    assert (
        rnode_support.guard_invalid_rnode_txpower_in_config(str(config_path)) is False
    )
    assert "interface_enabled = True" in config_path.read_text(encoding="utf-8")


def test_guard_disables_rnode_multi_with_invalid_nested_txpower(tmp_path):
    config_path = tmp_path / "config"
    config_path.write_text(
        """[interfaces]
[[RNode Multi]]
type = RNodeMultiInterface
interface_enabled = True

[[RNode Multi.r1]]
txpower = -9
""",
        encoding="utf-8",
    )

    assert rnode_support.guard_invalid_rnode_txpower_in_config(str(config_path)) is True
    assert (
        "interface_enabled = false" in config_path.read_text(encoding="utf-8").lower()
    )


def test_guard_invalid_txpower_honors_enabled_key(tmp_path):
    config_path = tmp_path / "config"
    config_path.write_text(
        """[interfaces]
[[Radio]]
type = RNodeInterface
enabled = yes
txpower = -9
""",
        encoding="utf-8",
    )

    assert rnode_support.guard_invalid_rnode_txpower_in_config(str(config_path)) is True
    assert (
        "interface_enabled = false" in config_path.read_text(encoding="utf-8").lower()
    )


def test_guard_invalid_txpower_skips_already_disabled(tmp_path):
    config_path = tmp_path / "config"
    config_path.write_text(
        """[interfaces]
[[Radio]]
type = RNodeInterface
interface_enabled = false
txpower = -9
""",
        encoding="utf-8",
    )

    assert (
        rnode_support.guard_invalid_rnode_txpower_in_config(str(config_path)) is False
    )


def test_optional_module_available_uses_find_spec(monkeypatch):
    monkeypatch.setattr(
        rnode_support.importlib.util,
        "find_spec",
        lambda name: object() if name == "present" else None,
    )
    assert rnode_support._optional_module_available("present") is True
    assert rnode_support._optional_module_available("missing") is False


def test_optional_module_available_handles_find_spec_errors(monkeypatch):
    def _boom(_name):
        raise ValueError("broken meta path")

    monkeypatch.setattr(rnode_support.importlib.util, "find_spec", _boom)
    assert rnode_support._optional_module_available("anything") is False


@settings(max_examples=200, deadline=None)
@given(
    prefix=st.sampled_from(["tcp://", "TCP://", "  tcp://"]),
    host=st.text(
        alphabet=st.characters(blacklist_categories=("Cs",), blacklist_characters="/"),
        min_size=1,
        max_size=32,
    ),
)
def test_rnode_port_is_tcp_never_false_positive_on_tcp_prefix(prefix, host):
    assert rnode_support.rnode_port_is_tcp(f"{prefix}{host}") is True


@settings(max_examples=200, deadline=None)
@given(
    noise=st.text(min_size=0, max_size=16),
)
def test_rnode_port_is_tcp_rejects_non_tcp_prefixes(noise):
    candidate = noise.strip()
    if candidate.lower().startswith("tcp://"):
        return
    assert rnode_support.rnode_port_is_tcp(candidate) is False


def test_normalize_rnode_tcp_host_backfills_rnode_ip_interface(tmp_path):
    config_path = tmp_path / "config"
    config_path.write_text(
        """[interfaces]
[[RNode IP]]
type = RNodeIPInterface
interface_enabled = True
port = tcp://192.0.2.5:4242
""",
        encoding="utf-8",
    )

    assert rnode_support.normalize_rnode_tcp_host_in_config(str(config_path)) is True
    assert "tcp_host = 192.0.2.5:4242" in config_path.read_text(encoding="utf-8")


def test_rnode_transport_supported_ble_on_desktop_needs_bleak(monkeypatch):
    monkeypatch.setattr(rnode_support, "desktop_ble_stack_available", lambda: False)
    monkeypatch.setattr(rnode_support, "desktop_serial_stack_available", lambda: True)

    assert (
        rnode_support.rnode_transport_supported(
            {"port": "ble://aa:bb:cc:dd:ee:ff"},
            is_android=False,
        )
        is False
    )


def test_rnode_transport_supported_ble_on_desktop_with_bleak(monkeypatch):
    monkeypatch.setattr(rnode_support, "desktop_ble_stack_available", lambda: True)

    assert (
        rnode_support.rnode_transport_supported(
            {"port": "ble://aa:bb:cc:dd:ee:ff"},
            is_android=False,
        )
        is True
    )


def test_disable_rnode_skips_sub_interface_siblings(tmp_path, monkeypatch):
    config_path = tmp_path / "config"
    config_path.write_text(
        """[interfaces]
[[RNode Multi]]
type = RNodeMultiInterface
interface_enabled = True

[[RNode Multi.r1]]
txpower = 7
frequency = 868000000
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(rnode_support, "_is_chaquopy_android", lambda: True)

    assert rnode_support.guard_rnode_interfaces_on_android(str(config_path)) is True
    text = config_path.read_text(encoding="utf-8")
    assert "interface_enabled = false" in text.lower()
    assert "txpower = 7" in text


def test_startup_repair_sequence_applies_all_guards(tmp_path, monkeypatch):
    config_path = tmp_path / "config"
    config_path.write_text(
        """[interfaces]
[[RNode TCP]]
type = RNodeInterface
interface_enabled = True
port = tcp://192.0.2.1:4242
txpower = -9

[[RNode Serial]]
type = RNodeInterface
interface_enabled = True
port = /dev/ttyUSB0
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(rnode_support, "_is_chaquopy_android", lambda: True)
    monkeypatch.setattr(rnode_support, "android_usbserial4a_available", lambda: False)
    monkeypatch.setattr(rnode_support, "android_jnius_available", lambda: False)

    assert rnode_support.normalize_rnode_tcp_host_in_config(str(config_path)) is True
    assert rnode_support.guard_rnode_interfaces_on_android(str(config_path)) is True
    assert rnode_support.guard_invalid_rnode_txpower_in_config(str(config_path)) is True

    text = config_path.read_text(encoding="utf-8")
    assert "tcp_host = 192.0.2.1:4242" in text
    assert text.lower().count("interface_enabled = false") == 2


@settings(max_examples=100, deadline=None)
@given(
    host=st.from_regex(r"[A-Za-z0-9][A-Za-z0-9.-]{0,31}", fullmatch=True),
    port=st.integers(min_value=1, max_value=65535),
)
def test_tcp_host_from_port_round_trips_host_port(host, port):
    value = f"tcp://{host}:{port}"
    assert rnode_support._tcp_host_from_port(value) == f"{host}:{port}"
