# SPDX-License-Identifier: 0BSD

import os
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
        ll.os,
        "uname",
        return_value=type("U", (), {"release": "6.12.7"})(),
    ):
        assert ll._kernel_version_meets_minimum() is True
    with patch.object(
        ll.os,
        "uname",
        return_value=type("U", (), {"release": "5.12.99"})(),
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


def test_landlock_kernel_supported_false_on_android(monkeypatch):
    """Android seccomp blocks Landlock syscalls with SIGSYS."""
    monkeypatch.delenv("MESHCHAT_LANDLOCK", raising=False)
    ll._landlock_support_cached = None
    with patch.object(ll, "sys") as mock_sys:
        mock_sys.platform = "linux"
        mock_sys.getandroidapilevel = lambda: 34
        assert ll.landlock_kernel_supported() is False


@pytest.mark.skipif(sys.platform != "linux", reason="Landlock probe requires Linux")
def test_landlock_kernel_supported_on_linux():
    ll._landlock_support_cached = None
    supported = ll.landlock_kernel_supported()
    assert isinstance(supported, bool)


def test_collect_read_roots_includes_proc_for_psutil():
    roots = ll._collect_read_roots()
    assert "/proc" in roots


def test_collect_read_roots_includes_interpreter_prefix():
    roots = ll._collect_read_roots()
    exe = os.path.realpath(sys.executable)
    prefix = os.path.realpath(getattr(sys, "base_prefix", None) or sys.prefix)
    assert any(
        exe == root or exe.startswith(root.rstrip("/") + "/") for root in roots
    ), f"executable {exe!r} not covered by {roots!r}"
    assert any(
        prefix == root or prefix.startswith(root.rstrip("/") + "/") for root in roots
    ), f"prefix {prefix!r} not covered by {roots!r}"
    # Active venv root (sys.prefix) must be allowed even when base_prefix differs,
    # otherwise child Python cannot read pyvenv.cfg (Docker /opt/venv + rnsh).
    venv_prefix = os.path.realpath(sys.prefix)
    assert any(
        venv_prefix == root or venv_prefix.startswith(root.rstrip("/") + "/")
        for root in roots
    ), f"sys.prefix {venv_prefix!r} not covered by {roots!r}"


def test_collect_read_roots_includes_venv_root_for_pyvenv_cfg(tmp_path, monkeypatch):
    """Landlock must allow the venv root, not only …/bin (pyvenv.cfg sibling)."""
    venv = tmp_path / "opt" / "venv"
    bindir = venv / "bin"
    bindir.mkdir(parents=True)
    (venv / "pyvenv.cfg").write_text("home = /usr\n", encoding="utf-8")
    fake_python = bindir / "python"
    fake_python.write_text("#!/bin/sh\n", encoding="utf-8")

    class _FakeSys:
        platform = sys.platform
        executable = str(fake_python)
        prefix = str(venv)
        base_prefix = "/usr"
        path = list(sys.path)

    monkeypatch.setattr(ll, "sys", _FakeSys)
    monkeypatch.setattr(ll.site, "getsitepackages", lambda: [])
    monkeypatch.setattr(ll.site, "getusersitepackages", lambda: "")
    monkeypatch.setenv("VIRTUAL_ENV", str(venv))

    roots = {os.path.realpath(r) for r in ll._collect_read_roots()}
    assert os.path.realpath(str(venv)) in roots
    assert os.path.realpath(str(bindir)) in roots


def test_handled_access_fs_for_abi_gates_new_rights():
    abi1 = ll._handled_access_fs_for_abi(1)
    assert abi1 & ll._LANDLOCK_ACCESS_FS_REFER == 0
    assert abi1 & ll._LANDLOCK_ACCESS_FS_TRUNCATE == 0
    assert abi1 & ll._LANDLOCK_ACCESS_FS_IOCTL_DEV == 0
    assert abi1 & ll._LANDLOCK_ACCESS_FS_WRITE_FILE

    abi2 = ll._handled_access_fs_for_abi(2)
    assert abi2 & ll._LANDLOCK_ACCESS_FS_REFER
    assert abi2 & ll._LANDLOCK_ACCESS_FS_TRUNCATE == 0

    abi3 = ll._handled_access_fs_for_abi(3)
    assert abi3 & ll._LANDLOCK_ACCESS_FS_REFER
    assert abi3 & ll._LANDLOCK_ACCESS_FS_TRUNCATE
    assert abi3 & ll._LANDLOCK_ACCESS_FS_IOCTL_DEV == 0

    abi5 = ll._handled_access_fs_for_abi(5)
    assert abi5 & ll._LANDLOCK_ACCESS_FS_IOCTL_DEV
    # Network and UNIX-resolve rights stay unhandled on purpose.
    assert abi5 == ll._handled_access_fs_for_abi(10)


def test_rw_access_grants_new_rights_when_handled():
    handled = ll._handled_access_fs_for_abi(5)
    read_access = ll._read_access_for_handled(handled)
    rw_access = ll._rw_access_for_handled(handled)
    assert read_access & ll._LANDLOCK_ACCESS_FS_TRUNCATE == 0
    assert read_access & ll._LANDLOCK_ACCESS_FS_IOCTL_DEV == 0
    assert read_access & ll._LANDLOCK_ACCESS_FS_REFER == 0
    assert rw_access & ll._LANDLOCK_ACCESS_FS_TRUNCATE
    assert rw_access & ll._LANDLOCK_ACCESS_FS_IOCTL_DEV
    assert rw_access & ll._LANDLOCK_ACCESS_FS_REFER


def test_ruleset_attr_size_matches_abi():
    assert ll._ruleset_attr_size(1) == 8
    assert ll._ruleset_attr_size(3) == 8
    assert ll._ruleset_attr_size(4) == 16
    assert ll._ruleset_attr_size(5) == 16
    assert ll._ruleset_attr_size(6) == 24


def test_file_access_includes_truncate_with_write():
    handled = ll._handled_access_fs_for_abi(5)
    rw = ll._rw_access_for_handled(handled)
    file_access = ll._file_access_from_dir_access(rw, handled)
    assert file_access & ll._LANDLOCK_ACCESS_FS_WRITE_FILE
    assert file_access & ll._LANDLOCK_ACCESS_FS_TRUNCATE
    assert file_access & ll._LANDLOCK_ACCESS_FS_IOCTL_DEV


@pytest.mark.skipif(sys.platform != "linux", reason="Landlock probe requires Linux")
def test_landlock_abi_version_on_linux():
    ll._landlock_abi_cached = None
    ll._landlock_support_cached = None
    abi = ll.landlock_abi_version()
    assert isinstance(abi, int)
    assert abi >= 0
    if ll.landlock_kernel_supported():
        assert abi >= 1


@pytest.mark.skipif(
    sys.platform != "linux" or not ll.landlock_kernel_supported(),
    reason="Landlock apply requires a supported Linux kernel",
)
def test_apply_landlock_preserves_storage_write_and_truncate(tmp_path):
    """Apply sandbox in a subprocess and confirm RW + truncate still work."""
    import subprocess
    import textwrap
    from pathlib import Path

    storage = tmp_path / "storage"
    storage.mkdir()
    script = textwrap.dedent(
        f"""
        import os
        import sys
        from meshchatx.src.backend.landlock_sandbox import apply_landlock_sandbox

        storage = {str(storage)!r}
        os.environ["MESHCHAT_LANDLOCK"] = "1"
        ok = apply_landlock_sandbox(storage_dir=storage, log_dir=storage)
        if not ok:
            print("APPLY_FAILED")
            sys.exit(2)
        path = os.path.join(storage, "landlock-abi-check.txt")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("hello")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("truncated")
        with open(path, encoding="utf-8") as handle:
            data = handle.read()
        if data != "truncated":
            print("TRUNCATE_FAILED", repr(data))
            sys.exit(3)
        print("OK")
        """
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=str(Path(__file__).resolve().parents[2]),
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if "APPLY_FAILED" in result.stdout:
        pytest.skip("Landlock could not be applied in this environment")
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert "OK" in result.stdout
