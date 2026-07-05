# SPDX-License-Identifier: 0BSD


from meshchatx.src.backend import rnode_support


def test_guard_disables_rnode_when_usbserial4a_missing(tmp_path, monkeypatch):
    config_path = tmp_path / "config"
    config_path.write_text(
        """[interfaces]
    [[RNode Serial]]
    type = RNodeInterface
    interface_enabled = True
    port = ble://aa:bb:cc:dd:ee:ff
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(rnode_support, "_is_chaquopy_android", lambda: True)
    monkeypatch.setattr(rnode_support, "android_usbserial4a_available", lambda: False)
    monkeypatch.setattr(rnode_support, "android_jnius_available", lambda: False)

    assert rnode_support.guard_rnode_interfaces_on_android(str(config_path)) is True
    assert "interface_enabled = false" in config_path.read_text(encoding="utf-8")


def test_guard_disables_rnode_when_jnius_missing(tmp_path, monkeypatch):
    """usbserial4a alone is not enough: RNS's Android RNodeInterface also needs jnius.

    Chaquopy builds that bundle usbserial4a but not jnius still hit
    RNS.panic() (os._exit) for any RNode port type (serial, tcp://, ble://),
    since the jnius check runs before the transport is selected.
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
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(rnode_support, "_is_chaquopy_android", lambda: True)
    monkeypatch.setattr(rnode_support, "android_usbserial4a_available", lambda: True)
    monkeypatch.setattr(rnode_support, "android_jnius_available", lambda: True)

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
