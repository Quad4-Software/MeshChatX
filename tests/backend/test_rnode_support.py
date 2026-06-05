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

    assert rnode_support.guard_rnode_interfaces_on_android(str(config_path)) is True
    assert "interface_enabled = false" in config_path.read_text(encoding="utf-8")


def test_guard_keeps_rnode_when_usbserial4a_available(tmp_path, monkeypatch):
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

    assert rnode_support.guard_rnode_interfaces_on_android(str(config_path)) is False
    assert "interface_enabled = True" in config_path.read_text(encoding="utf-8")


def test_rnode_serial_supported_on_desktop(monkeypatch):
    monkeypatch.setattr(rnode_support, "_is_chaquopy_android", lambda: False)
    assert rnode_support.rnode_serial_supported() is True
