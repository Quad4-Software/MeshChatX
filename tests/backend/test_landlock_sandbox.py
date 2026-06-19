# SPDX-License-Identifier: 0BSD

import sys
from unittest.mock import patch

import pytest

from meshchatx.src.backend import landlock_sandbox as ll


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
    monkeypatch.setenv("MESHCHAT_LANDLOCK", "0")
    with patch.object(ll, "sys") as mock_sys:
        mock_sys.platform = "linux"
        assert ll.landlock_requested() is False
        assert ll.landlock_disabled_by_env() is True


def test_landlock_requested_force_enable_env(monkeypatch):
    monkeypatch.setenv("MESHCHAT_LANDLOCK", "1")
    with patch.object(ll, "sys") as mock_sys:
        mock_sys.platform = "linux"
        assert ll.landlock_requested() is True
        assert ll.landlock_auto_enabled() is False


def test_landlock_auto_when_supported(monkeypatch):
    monkeypatch.delenv("MESHCHAT_LANDLOCK", raising=False)
    ll._landlock_support_cached = None
    with (
        patch.object(ll, "sys") as mock_sys,
        patch.object(ll, "landlock_kernel_supported", return_value=True),
    ):
        mock_sys.platform = "linux"
        assert ll.landlock_requested() is True
        assert ll.landlock_auto_enabled() is True


def test_landlock_auto_off_when_kernel_unsupported(monkeypatch):
    monkeypatch.delenv("MESHCHAT_LANDLOCK", raising=False)
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
