# SPDX-License-Identifier: 0BSD
"""Tests for CDN webseed torrent builder."""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

_SCRIPT = Path("scripts/ci/make-release-torrent.py")
_WORKFLOW = Path(".github/workflows/build-release.yml")


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("make_release_torrent", _SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def torrent() -> ModuleType:
    return _load()


def test_bencode_scalars_and_sorted_dict(torrent: ModuleType) -> None:
    assert torrent.bencode(4) == b"i4e"
    assert torrent.bencode("hi") == b"2:hi"
    assert torrent.bencode(b"ab") == b"2:ab"
    assert torrent.bencode({"b": 1, "a": 2}) == b"d1:ai2e1:bi1ee"


def test_include_name_keeps_installers(torrent: ModuleType) -> None:
    assert torrent.include_name("ReticulumMeshChatX-v1-linux-x86_64.AppImage")
    assert torrent.include_name("meshchatx-py314-linux-x64.pyz")
    assert not torrent.include_name("latest.yml")
    assert not torrent.include_name("file.cosign.bundle")
    assert not torrent.include_name("MeshChatX-v1.torrent")


def test_local_dir_builds_webseed_torrent(torrent: ModuleType, tmp_path: Path) -> None:
    a = tmp_path / "meshchatx-linux-x86_64.AppImage"
    b = tmp_path / "meshchatx-linux-amd64.deb"
    a.write_bytes(b"A" * 100)
    b.write_bytes(b"B" * 40)
    out = tmp_path / "MeshChatX-v0.0.0.torrent"
    rc = torrent.main(
        [
            "--dir",
            str(tmp_path),
            "--tag",
            "v0.0.0",
            "--track",
            "release",
            "--out",
            str(out),
        ]
    )
    assert rc == 0
    raw = out.read_bytes()
    assert b"https://cdn.quad4.io/release/" in raw
    assert b"https://github.com/Quad4-Software/MeshChatX/releases/download/" in raw
    assert b"meshchatx-linux-x86_64.AppImage" in raw
    meta = out.with_suffix(".json").read_text()
    assert "magnet:?xt=urn:btih:" in meta
    hasher = torrent.PieceHasher(torrent.PIECE_LENGTH)
    hasher.feed(b"A" * 100)
    hasher.feed(b"B" * 40)
    pieces = hasher.finish()
    _raw, infohash, _mag = torrent.build_torrent(
        tag="v0.0.0",
        track="release",
        files=[(a.name, 100), (b.name, 40)],
        pieces=pieces,
    )
    assert (
        hashlib.sha1(
            torrent.bencode(
                {
                    "name": "v0.0.0",
                    "piece length": torrent.PIECE_LENGTH,
                    "pieces": pieces,
                    "files": [
                        {"length": 100, "path": [a.name]},
                        {"length": 40, "path": [b.name]},
                    ],
                }
            )
        ).hexdigest()
        == infohash
    )


def test_workflow_builds_torrent_before_upload() -> None:
    text = _WORKFLOW.read_text()
    assert "make-release-torrent.py" in text
    torrent_at = text.index("make-release-torrent.py")
    upload_at = text.index("github-draft-release-upload-assets.sh")
    assert torrent_at < upload_at
