import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from lxmfy import landlock_sandbox as ll


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


def test_landlock_unsupported_without_package(monkeypatch):
    monkeypatch.setattr(ll, "landlockpy", None)
    ll._landlock_support_cached = None
    assert ll.landlock_kernel_supported() is False
    assert ll.apply_landlock_sandbox() is False


@pytest.mark.skipif(sys.platform != "linux", reason="Landlock probe requires Linux")
def test_landlock_kernel_supported_on_linux():
    ll._landlock_support_cached = None
    supported = ll.landlock_kernel_supported()
    assert isinstance(supported, bool)


def test_collect_read_roots_includes_proc_for_psutil():
    roots = ll._collect_read_roots()
    assert "/proc" in roots


def test_collect_rw_roots_temp_only():
    import tempfile

    roots = ll._collect_rw_roots(None, None, None, None, None, temp_only=True)
    assert roots == [os.path.abspath(tempfile.gettempdir())]


def test_landlock_status_dict():
    status = ll.landlock_status_dict(active=True, config_enabled=True)
    assert status["landlock_active"] is True
    assert "landlock_kernel_supported" in status
    assert "landlock_requested" in status


@pytest.mark.skipif(
    sys.platform != "linux" or not ll.landlock_kernel_supported(),
    reason="requires a Landlock-capable Linux kernel",
)
def test_apply_landlock_sandbox_enforces(tmp_path):
    """Apply the real sandbox in a subprocess and verify denial and grants.

    Enforcement is irreversible per-process, so it runs in a child. The
    child writes to its temp root (allowed), reads an /etc file (read
    root), then attempts writes outside every allowed root (denied).
    """
    child = """
import os
import sys
import tempfile

from lxmfy.landlock_sandbox import apply_landlock_sandbox

if not apply_landlock_sandbox(temp_only=True, config_enabled=True):
    sys.exit(2)

probe = os.path.join(tempfile.gettempdir(), "lxmfy_ll_probe")
with open(probe, "w") as f:
    f.write("ok")
with open("/etc/hostname") as f:
    f.read(1)

try:
    with open("/etc/lxmfy_ll_denied", "w") as f:
        f.write("x")
    sys.exit(3)
except OSError:
    pass

try:
    with open(os.path.expanduser("~/.bashrc")) as f:
        f.read(1)
    sys.exit(4)
except OSError:
    pass

sys.exit(0)
"""
    env = os.environ.copy()
    repo_root = str(Path(__file__).resolve().parent.parent)
    env["PYTHONPATH"] = repo_root + os.pathsep + env.get("PYTHONPATH", "")
    env["LXMFY_LANDLOCK"] = "1"
    result = subprocess.run(
        [sys.executable, "-c", child],
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0, result.stderr
