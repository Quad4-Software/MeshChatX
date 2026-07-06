# SPDX-License-Identifier: 0BSD


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
