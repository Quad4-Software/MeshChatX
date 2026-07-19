"""Version and MeshChatX-facing API readiness checks."""

from __future__ import annotations

import importlib.metadata
from pathlib import Path

import pytest

pytestmark = [pytest.mark.smoke, pytest.mark.unit]


def test_version_is_1_0_0():
    import rns_filesync

    assert rns_filesync.__version__ == "1.0.0"


def test_pyproject_version_matches_package():
    import rns_filesync

    root = Path(__file__).resolve().parents[2]
    text = (root / "pyproject.toml").read_text(encoding="utf-8")
    assert 'version = "1.0.0"' in text
    assert rns_filesync.__version__ == "1.0.0"


def test_distribution_metadata_when_installed():
    try:
        meta = importlib.metadata.version("rns-filesync")
    except importlib.metadata.PackageNotFoundError:
        pytest.skip("editable/distribution metadata unavailable")
    assert meta == "1.0.0"


def test_public_api_surface_for_meshchatx():
    from rns_filesync import FileSyncService
    from rns_filesync.permissions import PermissionStore

    required = [
        "start",
        "stop",
        "get_status",
        "list_peers",
        "list_files",
        "connect_peer",
        "disconnect_peer",
        "browse_peer",
        "download_file",
        "announce_now",
    ]
    for name in required:
        assert callable(getattr(FileSyncService, name, None)), name

    # Callback attributes exist on instances constructed without reticulum.
    from types import SimpleNamespace

    svc = FileSyncService(
        identity=SimpleNamespace(hash=b"\xaa" * 16),
        sync_directory="/tmp",
        permissions=PermissionStore(),
    )
    for attr in (
        "on_peer_connected",
        "on_peer_disconnected",
        "on_sync_progress",
        "on_file_updated",
        "on_file_deleted",
        "on_error",
    ):
        assert hasattr(svc, attr)


def test_service_does_not_construct_reticulum_when_instance_provided(tmp_path):
    """Embed contract: host-owned stack is reused."""
    from types import SimpleNamespace
    from unittest.mock import MagicMock

    import RNS

    from rns_filesync.service import FileSyncService

    fake = MagicMock(name="HostReticulum")
    existing = RNS.Reticulum.get_instance()
    if existing is not None:
        pytest.skip("reticulum already running in this process")

    svc = FileSyncService(
        identity=SimpleNamespace(hash=b"\xbb" * 16),
        sync_directory=str(tmp_path),
        reticulum=fake,
    )
    assert svc._ensure_reticulum() is fake
    assert svc._own_reticulum is False


def test_cli_module_importable():
    from rns_filesync import cli

    assert callable(cli.main)
    assert callable(cli.build_parser)
    parser = cli.build_parser()
    help_text = parser.format_help()
    assert "--rnsconfig" in help_text
    assert "--config" in help_text
    assert "--version" in help_text
    assert "--verbose" in help_text


def test_cli_version_flags(capsys):
    from rns_filesync import cli
    from rns_filesync._meta import __version__

    with pytest.raises(SystemExit) as exited:
        cli.build_parser().parse_args(["-v"])
    assert exited.value.code == 0
    out = capsys.readouterr().out
    assert __version__ in out
    assert "rns-filesync" in out

    with pytest.raises(SystemExit) as exited:
        cli.build_parser().parse_args(["--version"])
    assert exited.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_version_string_includes_baked_fields_when_set(monkeypatch):
    import rns_filesync._meta as meta

    monkeypatch.setattr(meta, "__version__", "1.0.0")
    monkeypatch.setattr(meta, "BUILD_DATE", "2026-07-19T12:00:00Z")
    monkeypatch.setattr(meta, "GIT_COMMIT", "deadbeef")
    monkeypatch.setattr(meta, "GIT_DIRTY", "0")
    text = meta.version_string()
    assert text == "rns-filesync 1.0.0 | built 2026-07-19T12:00:00Z | commit deadbeef"


def test_man_page_exists():
    root = Path(__file__).resolve().parents[2]
    man = root / "man" / "man1" / "rns-filesync.1"
    assert man.is_file()
    text = man.read_text(encoding="utf-8")
    assert ".TH RNS-FILESYNC" in text
    assert "--version" in text or "\\-\\-version" in text
