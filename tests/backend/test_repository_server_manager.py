# SPDX-License-Identifier: 0BSD

import time
import urllib.request
from unittest.mock import patch

import pytest

from meshchatx.src.backend.repository_server_manager import (
    RepositoryServerManager,
    build_repository_index_html,
    bundled_pip_targets,
    download_bundled_wheels_to_directory,
    meshchat_bundle_project_root,
    stage_local_meshchatx_wheel_into_bundled_dir,
)


def test_bundled_pip_targets_includes_extra_from_env(monkeypatch):
    monkeypatch.setenv("MESHCHAT_REPOSITORY_EXTRA_PIP", "foo, bar")
    names = bundled_pip_targets()
    assert "foo" in names
    assert "bar" in names
    assert "rns" in names
    assert "rnspure" in names


def test_seed_copies_bundled_wheels_from_public(tmp_path):
    identity = tmp_path / "identity"
    identity.mkdir()
    public = tmp_path / "public"
    bundled_pub = public / "repository-server-bundled" / "bundled"
    bundled_pub.mkdir(parents=True)
    (bundled_pub / "from_build.whl").write_bytes(b"wheeldata")
    mgr = RepositoryServerManager(str(identity), public_dir=str(public))
    rows = mgr.list_entries()
    bundled_names = [r["name"] for r in rows if r["source"] == "bundled"]
    assert "from_build.whl" in bundled_names


def test_seed_skips_when_wheel_already_present_same_size(tmp_path):
    identity = tmp_path / "identity"
    identity.mkdir()
    public = tmp_path / "public"
    bundled_pub = public / "repository-server-bundled" / "bundled"
    bundled_pub.mkdir(parents=True)
    (bundled_pub / "same.whl").write_bytes(b"aaaaaaaaaaaa")
    dest = identity / "repository-server" / "bundled"
    dest.mkdir(parents=True)
    (dest / "same.whl").write_bytes(b"bbbbbbbbbbbb")
    RepositoryServerManager(str(identity), public_dir=str(public))
    assert (dest / "same.whl").read_bytes() == b"bbbbbbbbbbbb"


def test_seed_replaces_bundled_when_public_wheel_size_differs(tmp_path):
    identity = tmp_path / "identity"
    identity.mkdir()
    public = tmp_path / "public"
    bundled_pub = public / "repository-server-bundled" / "bundled"
    bundled_pub.mkdir(parents=True)
    (bundled_pub / "mesh.whl").write_bytes(b"slim_wheel_from_build")
    dest = identity / "repository-server" / "bundled"
    dest.mkdir(parents=True)
    (dest / "mesh.whl").write_bytes(b"fat_old")
    RepositoryServerManager(str(identity), public_dir=str(public))
    assert (dest / "mesh.whl").read_bytes() == b"slim_wheel_from_build"


def test_meshchat_bundle_project_root_exists():
    root = meshchat_bundle_project_root()
    assert root is not None
    assert (root / "pyproject.toml").is_file()
    assert (root / "meshchatx").is_dir()


def test_stage_local_meshchatx_wheel_copies_newest(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()
    (root / "pyproject.toml").write_text(
        'name = "reticulum-meshchatx"\nversion = "0.0.0"\n', encoding="utf-8"
    )
    (root / "meshchatx").mkdir()
    dist = root / "dist"
    dist.mkdir()
    older = dist / "reticulum_meshchatx-1.0.0-py3-none-any.whl"
    newer = dist / "reticulum_meshchatx-2.0.0-py3-none-any.whl"
    older.write_bytes(b"old")
    time.sleep(0.02)
    newer.write_bytes(b"new")
    dest = tmp_path / "bundled"
    dest.mkdir()
    with patch(
        "meshchatx.src.backend.repository_server_manager.meshchat_bundle_project_root",
        return_value=root,
    ):
        out = stage_local_meshchatx_wheel_into_bundled_dir(dest)
    assert out is not None
    assert out.name == newer.name
    assert (dest / newer.name).read_bytes() == b"new"
    assert not (dest / older.name).exists()


def test_build_repository_index_html_lists_files(tmp_path):
    bundled = tmp_path / "bundled"
    uploads = tmp_path / "uploads"
    bundled.mkdir()
    uploads.mkdir()
    (bundled / "pkg.whl").write_bytes(b"x")
    (uploads / "note.txt").write_bytes(b"ab")
    html_out = build_repository_index_html(str(bundled), str(uploads))
    assert "MeshChatX repository" in html_out
    assert "pkg.whl" in html_out
    assert "note.txt" in html_out
    assert 'href="bundled/' in html_out
    assert 'href="uploads/' in html_out


def test_save_list_delete_upload(tmp_path):
    mgr = RepositoryServerManager(str(tmp_path))
    ok, err = mgr.save_upload("test.whl", b"abc")
    assert ok and err is None
    rows = mgr.list_entries()
    assert len(rows) == 1
    assert rows[0]["name"] == "test.whl"
    assert rows[0]["source"] == "upload"
    ok2, err2 = mgr.delete_upload("test.whl")
    assert ok2 and err2 is None
    assert mgr.list_entries() == []


def test_save_rejects_bad_filename(tmp_path):
    mgr = RepositoryServerManager(str(tmp_path))
    ok, err = mgr.save_upload("../evil.whl", b"x")
    assert not ok


@pytest.mark.parametrize(
    "name",
    [
        "x<script>.whl",
        "a b.whl",
        "wheel\x00.wheel",
        "subdir/x.whl",
        "",
        "bad!.whl",
    ],
)
def test_save_rejects_invalid_upload_filenames(tmp_path, name):
    mgr = RepositoryServerManager(str(tmp_path))
    ok, err = mgr.save_upload(name, b"x")
    assert not ok


@patch(
    "meshchatx.src.backend.repository_server_manager.download_bundled_wheels_to_directory"
)
def test_refresh_invokes_bundled_downloader(mock_dl, tmp_path):
    mock_dl.return_value = {"ok": True, "downloaded": ["rns"], "failed": {}}
    mgr = RepositoryServerManager(str(tmp_path))
    out = mgr.refresh_bundled_wheels()
    assert out["ok"] is True
    mock_dl.assert_called_once()
    assert mock_dl.call_args.kwargs.get("on_package") is not None


@patch(
    "meshchatx.src.backend.repository_server_manager.stage_local_meshchatx_wheel_into_bundled_dir",
    return_value=None,
)
@patch("meshchatx.src.backend.repository_server_manager._download_wheel_via_pypi_index")
def test_download_bundled_wheels_to_directory(mock_pypi, _mock_stage, tmp_path, monkeypatch):
    monkeypatch.setenv("MESHCHAT_REPOSITORY_EXTRA_PIP", "")
    mock_pypi.return_value = (True, None)
    dest = tmp_path / "out"
    out = download_bundled_wheels_to_directory(dest)
    n = len(bundled_pip_targets())
    assert out["ok"] is True
    assert len(out["downloaded"]) == n
    assert not out["failed"]
    assert mock_pypi.call_count == n


@patch(
    "meshchatx.src.backend.repository_server_manager.stage_local_meshchatx_wheel_into_bundled_dir",
    return_value=None,
)
@patch("meshchatx.src.backend.repository_server_manager._download_wheel_via_pypi_index")
def test_download_bundled_wheels_records_pypi_failures(
    mock_pypi, _mock_stage, tmp_path, monkeypatch
):
    monkeypatch.setenv("MESHCHAT_REPOSITORY_EXTRA_PIP", "")
    mock_pypi.return_value = (False, "offline")
    dest = tmp_path / "out"
    out = download_bundled_wheels_to_directory(dest)
    n = len(bundled_pip_targets())
    assert out["ok"] is False
    assert not out["downloaded"]
    assert len(out["failed"]) == n
    assert mock_pypi.call_count == n


@patch(
    "meshchatx.src.backend.repository_server_manager.stage_local_meshchatx_wheel_into_bundled_dir",
    return_value=None,
)
@patch("meshchatx.src.backend.repository_server_manager._download_wheel_via_pypi_index")
def test_refresh_bundled_wheels_fails_when_pypi_unavailable(
    mock_pypi, _mock_stage, tmp_path, monkeypatch
):
    monkeypatch.setenv("MESHCHAT_REPOSITORY_EXTRA_PIP", "")
    mock_pypi.return_value = (False, "offline")
    mgr = RepositoryServerManager(str(tmp_path))
    out = mgr.refresh_bundled_wheels()
    assert out["ok"] is False
    assert not out["downloaded"]


def test_http_start_stop_and_status(tmp_path):
    mgr = RepositoryServerManager(str(tmp_path))
    assert mgr.status()["http"]["running"] is False
    first = mgr.start_http_server("127.0.0.1", 0)
    assert first["ok"] is True
    assert first["port"] > 0
    time.sleep(0.05)
    st = mgr.status()["http"]
    assert st["running"] is True
    assert st["url"] == f"http://127.0.0.1:{first['port']}/"
    assert st["last_port"] == first["port"]
    second = mgr.start_http_server("127.0.0.1", first["port"])
    assert second["ok"] is False
    assert second["error"] == "already_running"
    mgr.stop_http_server()
    assert mgr.status()["http"]["running"] is False


def test_http_invalid_host(tmp_path):
    mgr = RepositoryServerManager(str(tmp_path))
    out = mgr.start_http_server("   ", 8787)
    assert out["ok"] is False
    assert out["error"] == "invalid_host"


def test_http_get_root(tmp_path):
    mgr = RepositoryServerManager(str(tmp_path))
    mgr.save_upload("listed.whl", b"wheel")
    out = mgr.start_http_server("127.0.0.1", 0)
    assert out["ok"] is True
    time.sleep(0.08)
    url = out["url"]
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            assert resp.status == 200
            body = resp.read().decode("utf-8")
            assert "listed.whl" in body
            assert "uploads/" in body
    finally:
        mgr.stop_http_server()


def test_http_restart_uses_last_listen(tmp_path):
    mgr = RepositoryServerManager(str(tmp_path))
    a = mgr.start_http_server("127.0.0.1", 0)
    assert a["ok"] is True
    port = a["port"]
    mgr.stop_http_server()
    b = mgr.restart_http_server(None, None)
    assert b["ok"] is True
    assert b["port"] == port
    mgr.stop_http_server()
