# SPDX-License-Identifier: 0BSD

"""Tests for optional seccomp-BPF sandbox."""

import sys
from unittest.mock import MagicMock, patch

import pytest

from meshchatx.src.backend import seccomp_sandbox as sc


@pytest.fixture(autouse=True)
def _reset_seccomp_caches():
    sc._seccomp_support_cached = None
    sc._seccomp_lib_cached = None
    sc._seccomp_lib_failed = False
    yield
    sc._seccomp_support_cached = None
    sc._seccomp_lib_cached = None
    sc._seccomp_lib_failed = False


def test_seccomp_requested_non_linux():
    with (
        patch.object(sc.sys, "platform", "darwin"),
        patch.object(sc, "_is_android", return_value=False),
    ):
        assert sc.seccomp_requested() is False


def test_seccomp_requested_respects_disable_env(monkeypatch):
    monkeypatch.setenv("MESHCHAT_SECCOMP", "0")
    with (
        patch.object(sc.sys, "platform", "linux"),
        patch.object(sc, "_is_android", return_value=False),
    ):
        assert sc.seccomp_requested() is False
        assert sc.seccomp_disabled_by_env() is True


def test_seccomp_requested_force_enable_env(monkeypatch):
    monkeypatch.setenv("MESHCHAT_SECCOMP", "1")
    with (
        patch.object(sc.sys, "platform", "linux"),
        patch.object(sc, "_is_android", return_value=False),
    ):
        assert sc.seccomp_requested() is True
        assert sc.seccomp_auto_enabled() is False


def test_seccomp_auto_when_supported(monkeypatch):
    monkeypatch.delenv("MESHCHAT_SECCOMP", raising=False)
    with (
        patch.object(sc.sys, "platform", "linux"),
        patch.object(sc, "_is_android", return_value=False),
        patch.object(sc, "seccomp_kernel_supported", return_value=True),
    ):
        assert sc.seccomp_requested() is True
        assert sc.seccomp_auto_enabled() is True


def test_seccomp_auto_off_when_unsupported(monkeypatch):
    monkeypatch.delenv("MESHCHAT_SECCOMP", raising=False)
    with (
        patch.object(sc.sys, "platform", "linux"),
        patch.object(sc, "_is_android", return_value=False),
        patch.object(sc, "seccomp_kernel_supported", return_value=False),
    ):
        assert sc.seccomp_requested() is False


def test_seccomp_kernel_supported_false_on_android():
    with patch.object(sc, "_is_android", return_value=True):
        assert sc.seccomp_kernel_supported() is False


def test_apply_seccomp_falls_back_when_not_requested(monkeypatch):
    monkeypatch.setenv("MESHCHAT_SECCOMP", "0")
    assert sc.apply_seccomp_sandbox() is False


def test_apply_seccomp_falls_back_without_libseccomp(monkeypatch):
    monkeypatch.setenv("MESHCHAT_SECCOMP", "1")
    with (
        patch.object(sc.sys, "platform", "linux"),
        patch.object(sc, "_is_android", return_value=False),
        patch.object(sc, "_load_libseccomp", return_value=None),
    ):
        assert sc.apply_seccomp_sandbox() is False


def test_apply_seccomp_loads_denylist(monkeypatch):
    monkeypatch.setenv("MESHCHAT_SECCOMP", "1")
    lib = MagicMock()
    ctx = object()
    lib.seccomp_init.return_value = ctx
    lib.seccomp_syscall_resolve_name.side_effect = lambda name: {
        b"mount": 165,
        b"ptrace": 101,
        b"bpf": 321,
    }.get(name, -1)
    lib.seccomp_rule_add.return_value = 0
    lib.seccomp_load.return_value = 0

    with (
        patch.object(sc.sys, "platform", "linux"),
        patch.object(sc, "_is_android", return_value=False),
        patch.object(sc, "_load_libseccomp", return_value=lib),
    ):
        assert sc.apply_seccomp_sandbox() is True

    lib.seccomp_init.assert_called_once_with(sc._SCMP_ACT_ALLOW)
    assert lib.seccomp_rule_add.call_count >= 3
    lib.seccomp_load.assert_called_once_with(ctx)
    lib.seccomp_release.assert_called_once_with(ctx)


@pytest.mark.skipif(sys.platform != "linux", reason="seccomp probe requires Linux")
def test_seccomp_kernel_supported_on_linux():
    supported = sc.seccomp_kernel_supported()
    assert isinstance(supported, bool)
