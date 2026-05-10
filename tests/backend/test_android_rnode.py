# SPDX-License-Identifier: 0BSD


import pytest

from meshchatx.meshchat import ReticulumMeshChat


def test_disable_rnode_interfaces_on_android(tmp_path):
    config_path = tmp_path / "config"
    config_path.write_text(
        """[reticulum]
enable_transport = False

[interfaces]
    [[RNode Serial]]
    type = RNodeInterface
    interface_enabled = True
    port = /dev/ttyUSB0
    frequency = 867200000
    bandwidth = 125000
    txpower = 7
    spreadingfactor = 8
    codingrate = 5

    [[TCP Client]]
    type = TCPClientInterface
    interface_enabled = True
    target_host = localhost
    target_port = 4242
""",
        encoding="utf-8",
    )

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "meshchatx.meshchat._is_chaquopy_android",
            lambda: True,
        )
        modified = ReticulumMeshChat._disable_rnode_interfaces_on_android(
            str(config_path),
        )

    assert modified is True
    content = config_path.read_text(encoding="utf-8")
    assert "interface_enabled = false" in content
    assert "type = RNodeInterface" in content
    assert "type = TCPClientInterface" in content


def test_disable_rnode_interfaces_skips_when_not_android(tmp_path):
    config_path = tmp_path / "config"
    config_path.write_text(
        """[interfaces]
    [[RNode Serial]]
    type = RNodeInterface
    interface_enabled = True
""",
        encoding="utf-8",
    )

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "meshchatx.meshchat._is_chaquopy_android",
            lambda: False,
        )
        modified = ReticulumMeshChat._disable_rnode_interfaces_on_android(
            str(config_path),
        )

    assert modified is False
    content = config_path.read_text(encoding="utf-8")
    assert "interface_enabled = True" in content


def test_disable_rnode_interfaces_handles_missing_config():
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "meshchatx.meshchat._is_chaquopy_android",
            lambda: True,
        )
        modified = ReticulumMeshChat._disable_rnode_interfaces_on_android(
            "/nonexistent/config",
        )
    assert modified is False


def test_get_android_external_files_dir_returns_none_on_desktop():
    from meshchatx.android_push_bridge import _get_android_external_files_dir

    assert _get_android_external_files_dir() is None
