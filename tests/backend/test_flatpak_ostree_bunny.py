# SPDX-License-Identifier: 0BSD
"""Tests for Flatpak channel mapping and Bunny OSTree ordered upload."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from unittest.mock import patch

import pytest

_CHANNEL = Path("scripts/ci/github_flatpak_channel.py")
_OSTREE_UPLOAD = Path("scripts/ci/github-upload-bunny-flatpak-ostree.py")
_EXPORT = Path("scripts/ci/github-flatpak-ostree-export.sh")
_WORKFLOW = Path(".github/workflows/build-release.yml")
_PAGES_WORKFLOW = Path(".github/workflows/flatpak-repo.yml")
_RELEASE_UPLOAD = Path("scripts/ci/github-upload-bunny-storage-release-assets.py")


def _load(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def channel() -> ModuleType:
    return _load(_CHANNEL, "flatpak_channel")


@pytest.fixture(scope="module")
def ostree_up() -> ModuleType:
    return _load(_OSTREE_UPLOAD, "flatpak_ostree_upload")


def test_flatpak_branch_from_ref_name(channel: ModuleType) -> None:
    assert (
        channel.flatpak_branch_from_ref_name("nightly-2026.09.03-abc1234") == "testing"
    )
    assert (
        channel.flatpak_branch_from_ref_name("testing-2026.09.03-abc1234") == "testing"
    )
    assert channel.flatpak_branch_from_ref_name("beta-2026.09.03-abc1234") == "beta"
    assert channel.flatpak_branch_from_ref_name("preview-dev-2026.09.03-abc") == "beta"
    assert channel.flatpak_branch_from_ref_name("v4.9.0") == "stable"
    assert channel.flatpak_branch_from_ref_name("4.9.0") == "stable"


def test_upload_phase_order(ostree_up: ModuleType) -> None:
    assert ostree_up.upload_phase(
        "repo/objects/ab/cdef.filez"
    ) < ostree_up.upload_phase("repo/deltas/xx/yy")
    assert ostree_up.upload_phase("repo/deltas/xx/yy") < ostree_up.upload_phase(
        "repo/config"
    )
    assert ostree_up.upload_phase("repo/config") < ostree_up.upload_phase(
        "repo/summary"
    )
    assert ostree_up.upload_phase("meshchatx.flatpakrepo") < ostree_up.upload_phase(
        "repo/summary"
    )
    assert ostree_up.upload_phase("repo/summary") < ostree_up.upload_phase(
        "repo/summary.sig"
    )
    assert ostree_up.upload_phase("repo/summary.sig") < ostree_up.upload_phase(
        "repo/summary.idx"
    )
    assert ostree_up.upload_phase("repo/summaries/x") < ostree_up.upload_phase(
        "repo/summary"
    )


def test_ordered_rel_paths_puts_summary_idx_last(
    ostree_up: ModuleType, tmp_path: Path
) -> None:
    root = tmp_path
    (root / "repo" / "objects" / "aa").mkdir(parents=True)
    (root / "repo" / "deltas" / "bb").mkdir(parents=True)
    (root / "repo" / "summaries").mkdir(parents=True)
    (root / "repo" / "objects" / "aa" / "obj").write_bytes(b"o")
    (root / "repo" / "deltas" / "bb" / "d").write_bytes(b"d")
    (root / "repo" / "config").write_text("mode=archive-z2\n", encoding="utf-8")
    (root / "repo" / "summary").write_bytes(b"s")
    (root / "repo" / "summary.sig").write_bytes(b"g")
    (root / "repo" / "summary.idx").write_bytes(b"i")
    (root / "repo" / "summaries" / "extra").write_bytes(b"e")
    (root / "meshchatx.flatpakrepo").write_text("[Flatpak Repo]\n", encoding="utf-8")

    ordered = ostree_up.ordered_rel_paths(root)
    assert ordered[0].startswith("repo/objects/")
    assert any(r.startswith("repo/deltas/") for r in ordered)
    assert ordered[-1] == "repo/summary.idx"
    assert ordered.index("repo/summary") < ordered.index("repo/summary.sig")
    assert ordered.index("repo/summary.sig") < ordered.index("repo/summary.idx")
    assert ordered.index("repo/config") < ordered.index("repo/summary")


def test_upload_ostree_tree_order_and_no_track_prune(
    ostree_up: ModuleType, tmp_path: Path
) -> None:
    root = tmp_path
    (root / "repo" / "objects" / "aa").mkdir(parents=True)
    (root / "repo" / "objects" / "aa" / "obj").write_bytes(b"o")
    (root / "repo" / "config").write_text("mode=archive-z2\n", encoding="utf-8")
    (root / "repo" / "summary").write_bytes(b"s")
    (root / "repo" / "summary.idx").write_bytes(b"i")

    puts: list[str] = []

    def fake_put(
        url: str,
        body: bytes,
        access_key: str,
        content_type: str,
        max_attempts: int = 4,
    ) -> None:
        puts.append(url)

    with (
        patch.object(ostree_up, "put_file", side_effect=fake_put),
        patch.object(ostree_up, "prune_remote_orphans") as prune,
    ):
        rc = ostree_up.upload_ostree_tree(
            root,
            "https://la.storage.bunnycdn.com/meshchatx",
            "key",
            prefix="flatpak",
            prune_orphans=True,
            workers=1,
        )
    assert rc == 0
    assert puts[0].endswith("/flatpak/repo/objects/aa/obj")
    assert puts[-1].endswith("/flatpak/repo/summary.idx")
    prune.assert_called_once()


def test_upload_ostree_tree_phase_barrier_with_workers(
    ostree_up: ModuleType, tmp_path: Path
) -> None:
    root = tmp_path
    objs = root / "repo" / "objects"
    for name in ("aa", "bb", "cc"):
        d = objs / name
        d.mkdir(parents=True)
        (d / "obj").write_bytes(name.encode())
    (root / "repo" / "config").write_text("mode=archive-z2\n", encoding="utf-8")
    (root / "repo" / "summary").write_bytes(b"s")
    (root / "repo" / "summary.idx").write_bytes(b"i")

    puts: list[str] = []

    def fake_put(
        url: str,
        body: bytes,
        access_key: str,
        content_type: str,
        max_attempts: int = 4,
    ) -> None:
        puts.append(url)

    with (
        patch.object(ostree_up, "put_file", side_effect=fake_put),
        patch.object(ostree_up, "prune_remote_orphans"),
    ):
        rc = ostree_up.upload_ostree_tree(
            root,
            "https://la.storage.bunnycdn.com/meshchatx",
            "key",
            prefix="flatpak",
            prune_orphans=False,
            workers=8,
        )
    assert rc == 0
    assert len(puts) == 6
    object_puts = [u for u in puts if "/repo/objects/" in u]
    assert len(object_puts) == 3
    assert all("/repo/objects/" in u for u in puts[:3])
    assert puts[3].endswith("/flatpak/repo/config")
    assert puts[4].endswith("/flatpak/repo/summary")
    assert puts[5].endswith("/flatpak/repo/summary.idx")


def test_workflow_flatpak_ostree_timeout_and_workers() -> None:
    text = _WORKFLOW.read_text(encoding="utf-8")
    assert "BUNNY_UPLOAD_WORKERS" in text
    # Job timeout must leave headroom for cold Bunny publishes.
    assert "timeout-minutes: 180" in text


def test_export_script_uses_cdn_meshchatx() -> None:
    text = _EXPORT.read_text(encoding="utf-8")
    assert "cdn.meshchatx.com/flatpak" in text
    assert "meshchatx-stable.flatpakref" in text
    assert "meshchatx-beta.flatpakref" in text
    assert "meshchatx-testing.flatpakref" in text
    assert "github.io" not in text
    assert "PAGES_URL" not in text


def test_workflow_wires_flatpak_ostree_not_pages() -> None:
    text = _WORKFLOW.read_text(encoding="utf-8")
    assert "flatpak-ostree:" in text
    assert "github-flatpak-ostree-export.sh" in text
    assert "github-upload-bunny-flatpak-ostree.py" in text
    assert "flatpak-ostree-bunny" in text
    assert "cdn.meshchatx.com/flatpak" in text
    assert "deploy-pages" not in text
    assert "upload-pages-artifact" not in text
    assert "needs.flatpak-ostree.result" in text
    assert not _PAGES_WORKFLOW.exists()


def test_release_asset_uploader_does_not_prune_flatpak_prefix() -> None:
    mod = _load(_RELEASE_UPLOAD, "bunny_release_upload")
    assert mod.parse_track_version("flatpak") is None
    assert mod.parse_track_version("flatpak/repo") is None
    assert mod.parse_track_version("release/v1.2.3") == ("release", "v1.2.3")
