"""Smoke tests for package import and CLI help."""

import subprocess
import sys

import pytest

pytestmark = pytest.mark.smoke


def test_import_package():
    from rns_filesync import FileSyncService, __version__

    assert FileSyncService is not None
    assert __version__


def test_cli_help():
    result = subprocess.run(
        [sys.executable, "-m", "rns_filesync.cli", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "directory" in result.stdout
