import sys
from unittest.mock import patch

import pytest

from lxmfy import landlock_sandbox as ll


def test_parse_kernel_version():
    assert ll._parse_kernel_version("6.12.7-1-cachyos-hardened") == (6, 12, 7)
    assert ll._parse_kernel_version("5.13.0") == (5, 13, 0)
    assert ll._parse_kernel_version("5.12.19") == (5, 12, 19)


def test_kernel_version_meets_minimum():
    with patch.object(
        ll.os, "uname", return_value=type("U", (), {"release": "6.12.7"})()
    ):
        assert ll._kernel_version_meets_minimum() is True
    with patch.object(
        ll.os, "uname", return_value=type("U", (), {"release": "5.12.99"})()
    ):
        assert ll._kernel_version_meets_minimum() is False


def test_landlock_requested_non_linux():
    with patch.object(ll, "sys") as mock_sys:
        mock_sys.platform = "darwin"
        assert ll.landlock_requested() is False


def test_landlock_requested_respects_disable_env(monkeypatch):
    monkeypatch.setenv("LXMFY_LANDLOCK", "0")
    with patch.object(ll, "sys") as mock_sys:
        mock_sys.platform = "linux"
        assert ll.landlock_requested() is False
        assert ll.landlock_disabled_by_env() is True


def test_landlock_requested_force_enable_env(monkeypatch):
    monkeypatch.setenv("LXMFY_LANDLOCK", "1")
    with patch.object(ll, "sys") as mock_sys:
        mock_sys.platform = "linux"
        assert ll.landlock_requested() is True
        assert ll.landlock_auto_enabled() is False


def test_landlock_requested_respects_config_disabled(monkeypatch):
    monkeypatch.delenv("LXMFY_LANDLOCK", raising=False)
    with (
        patch.object(ll, "sys") as mock_sys,
        patch.object(ll, "landlock_kernel_supported", return_value=True),
    ):
        mock_sys.platform = "linux"
        assert ll.landlock_requested(config_enabled=False) is False


def test_landlock_auto_when_supported(monkeypatch):
    monkeypatch.delenv("LXMFY_LANDLOCK", raising=False)
    ll._landlock_support_cached = None
    with (
        patch.object(ll, "sys") as mock_sys,
        patch.object(ll, "landlock_kernel_supported", return_value=True),
    ):
        mock_sys.platform = "linux"
        assert ll.landlock_requested() is True
        assert ll.landlock_auto_enabled() is True


def test_landlock_auto_off_when_kernel_unsupported(monkeypatch):
    monkeypatch.delenv("LXMFY_LANDLOCK", raising=False)
    with (
        patch.object(ll, "sys") as mock_sys,
        patch.object(ll, "landlock_kernel_supported", return_value=False),
    ):
        mock_sys.platform = "linux"
        assert ll.landlock_requested() is False
        assert ll.landlock_auto_enabled() is False


@pytest.mark.skipif(sys.platform != "linux", reason="Landlock probe requires Linux")
def test_landlock_kernel_supported_on_linux():
    ll._landlock_support_cached = None
    supported = ll.landlock_kernel_supported()
    assert isinstance(supported, bool)


def test_collect_read_roots_includes_proc_for_psutil():
    roots = ll._collect_read_roots()
    assert "/proc" in roots


def test_landlock_status_dict():
    status = ll.landlock_status_dict(active=True, config_enabled=True)
    assert status["landlock_active"] is True
    assert "landlock_kernel_supported" in status
    assert "landlock_requested" in status
    assert "landlock_abi_version" in status


def test_handled_access_fs_for_abi_gates_new_rights():
    abi1 = ll._handled_access_fs_for_abi(1)
    assert abi1 & ll._LANDLOCK_ACCESS_FS_REFER == 0
    assert abi1 & ll._LANDLOCK_ACCESS_FS_TRUNCATE == 0
    assert abi1 & ll._LANDLOCK_ACCESS_FS_IOCTL_DEV == 0

    abi5 = ll._handled_access_fs_for_abi(5)
    assert abi5 & ll._LANDLOCK_ACCESS_FS_REFER
    assert abi5 & ll._LANDLOCK_ACCESS_FS_TRUNCATE
    assert abi5 & ll._LANDLOCK_ACCESS_FS_IOCTL_DEV
    assert abi5 == ll._handled_access_fs_for_abi(10)


def test_rw_access_grants_new_rights_when_handled():
    handled = ll._handled_access_fs_for_abi(5)
    rw_access = ll._rw_access_for_handled(handled)
    read_access = ll._read_access_for_handled(handled)
    assert read_access & ll._LANDLOCK_ACCESS_FS_TRUNCATE == 0
    assert rw_access & ll._LANDLOCK_ACCESS_FS_TRUNCATE
    assert rw_access & ll._LANDLOCK_ACCESS_FS_IOCTL_DEV
    assert rw_access & ll._LANDLOCK_ACCESS_FS_REFER


def test_ruleset_attr_size_matches_abi():
    assert ll._ruleset_attr_size(1) == 8
    assert ll._ruleset_attr_size(4) == 16
    assert ll._ruleset_attr_size(6) == 24
