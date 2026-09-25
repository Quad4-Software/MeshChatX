# SPDX-License-Identifier: 0BSD
"""Unit and contract tests for Bunny Storage release asset upload."""

from __future__ import annotations

import importlib.util
import io
from pathlib import Path
from types import ModuleType
from typing import Any
from unittest.mock import patch

import pytest

_SCRIPT = Path("scripts/ci/github-upload-bunny-storage-release-assets.py")
_WORKFLOW = Path(".github/workflows/build-release.yml")


def _load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("bunny_upload", _SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def bunny() -> ModuleType:
    return _load_script()


def test_workflow_wires_bunny_upload() -> None:
    text = _WORKFLOW.read_text(encoding="utf-8")
    assert "github-upload-bunny-storage-release-assets.py" in text
    assert "BUNNY_STORAGE_ACCESS_KEY" in text
    assert "BUNNY_STORAGE_BASE_URL" in text
    assert "track=release" in text
    assert "track=testing" in text
    assert "track=beta" in text


def test_parse_track_version(bunny: ModuleType) -> None:
    assert bunny.parse_track_version("release/v1.2.3") == ("release", "v1.2.3")
    assert bunny.parse_track_version("testing/nightly-2026.09.02-abc1234") == (
        "testing",
        "nightly-2026.09.02-abc1234",
    )
    assert bunny.parse_track_version("nightly/nightly-2026.09.02-abc1234") == (
        "testing",
        "nightly-2026.09.02-abc1234",
    )
    assert bunny.parse_track_version("beta/beta-2026.09.02-abc1234") == (
        "beta",
        "beta-2026.09.02-abc1234",
    )
    assert bunny.parse_track_version("master/v1.0.0") is None
    assert bunny.parse_track_version("release") is None
    assert bunny.parse_track_version("release/a/b") is None


def test_should_skip_noise_files(bunny: ModuleType, tmp_path: Path) -> None:
    assert bunny.should_skip_file(tmp_path / "builder-debug.yml")
    assert bunny.should_skip_file(tmp_path / "win__builder-debug.yml")
    assert bunny.should_skip_file(tmp_path / "foo.so.yml")
    assert not bunny.should_skip_file(tmp_path / "MeshChatX.AppImage")


def test_mime_for_wasm(bunny: ModuleType, tmp_path: Path) -> None:
    assert bunny.mime_for(tmp_path / "x.wasm") == "application/wasm"


def test_prune_keeps_current_version(bunny: ModuleType) -> None:
    listing = [
        {"IsDirectory": True, "ObjectName": "v1.0.0", "LastChanged": "2026-01-01"},
        {"IsDirectory": True, "ObjectName": "v1.1.0", "LastChanged": "2026-02-01"},
        {"IsDirectory": False, "ObjectName": "readme.txt"},
    ]
    deleted: list[str] = []

    def fake_get_json(url: str, access_key: str, timeout: int = 120) -> object:
        assert url.endswith("/release/")
        return listing

    def fake_delete(url: str, access_key: str, timeout: int = 120) -> None:
        deleted.append(url)

    with (
        patch.object(bunny, "get_json", side_effect=fake_get_json),
        patch.object(bunny, "delete_path", side_effect=fake_delete),
    ):
        bunny.prune_other_versions(
            "https://la.storage.bunnycdn.com/meshchatx",
            "key",
            "release",
            "v1.1.0",
            keep_count=1,
        )

    assert len(deleted) == 1
    assert deleted[0].endswith("/release/v1.0.0")
    assert "v1.1.0" not in deleted[0]


def test_prune_keeps_newest_four_by_last_changed(bunny: ModuleType) -> None:
    """Six version dirs sorted by LastChanged keep the newest four.

    The rest are deleted regardless of name ordering.
    """
    listing = [
        {
            "IsDirectory": True,
            "ObjectName": "v4.9.9",
            "LastChanged": "2026-05-01T00:00:00",
        },
        {
            "IsDirectory": True,
            "ObjectName": "v4.9.10",
            "LastChanged": "2026-03-01T00:00:00",
        },
        {
            "IsDirectory": True,
            "ObjectName": "v4.9.1",
            "LastChanged": "2026-09-01T00:00:00",
        },
        {
            "IsDirectory": True,
            "ObjectName": "v4.9.2",
            "LastChanged": "2026-08-01T00:00:00",
        },
        {
            "IsDirectory": True,
            "ObjectName": "v4.9.3",
            "LastChanged": "2026-07-01T00:00:00",
        },
        {
            "IsDirectory": True,
            "ObjectName": "v4.9.4",
            "LastChanged": "2026-06-01T00:00:00",
        },
        {
            "IsDirectory": False,
            "ObjectName": "stray.txt",
            "LastChanged": "2026-09-05T00:00:00",
        },
    ]
    deleted: list[str] = []

    def fake_get_json(url: str, access_key: str, timeout: int = 120) -> object:
        return listing

    def fake_delete(url: str, access_key: str, timeout: int = 120) -> None:
        deleted.append(url)

    with (
        patch.object(bunny, "get_json", side_effect=fake_get_json),
        patch.object(bunny, "delete_path", side_effect=fake_delete),
    ):
        bunny.prune_other_versions(
            "https://la.storage.bunnycdn.com/meshchatx",
            "key",
            "testing",
            "testing-today",
        )

    deleted_names = {url.rsplit("/", 1)[-1] for url in deleted}
    # Newest four by LastChanged: v4.9.1 v4.9.2 v4.9.3 v4.9.4; keep_version
    # testing-today (not in listing). Oldest two are deleted.
    assert deleted_names == {"v4.9.9", "v4.9.10"}
    assert not any("stray.txt" in d for d in deleted)


def test_prune_all_tracks_prunes_each_track(bunny: ModuleType) -> None:
    calls: list[tuple[str, str]] = []

    def fake_prune(
        base: str,
        access_key: str,
        track: str,
        keep_version: str,
        keep_count: int = bunny.KEEP_VERSIONS,
    ) -> None:
        calls.append((track, keep_version))

    with patch.object(bunny, "prune_other_versions", side_effect=fake_prune):
        assert bunny.prune_all_tracks("https://x.test", "key") == 0

    assert sorted(track for track, _ in calls) == ["beta", "release", "testing"]


def test_upload_then_prune(bunny: ModuleType, tmp_path: Path) -> None:
    root = tmp_path / "upload"
    root.mkdir()
    (root / "MeshChatX.AppImage").write_bytes(b"payload")
    (root / "builder-debug.yml").write_text("noise\n", encoding="utf-8")

    events: list[str] = []

    def fake_put(
        url: str,
        body: bytes,
        access_key: str,
        content_type: str,
        max_attempts: int = 4,
    ) -> None:
        events.append(f"put:{url}")
        assert body == b"payload"

    def fake_prune(
        base: str,
        access_key: str,
        track: str,
        keep_version: str,
    ) -> None:
        events.append(f"prune:{track}:{keep_version}")

    with (
        patch.object(bunny, "put_file", side_effect=fake_put),
        patch.object(bunny, "prune_other_versions", side_effect=fake_prune),
        patch.object(bunny, "_list_remote_checksums", return_value={}),
    ):
        code = bunny.upload_tree(
            root,
            "https://la.storage.bunnycdn.com/meshchatx",
            "key",
            "release/v9.9.9",
        )

    assert code == 0
    assert events[0].startswith("put:")
    assert "MeshChatX.AppImage" in events[0]
    assert "builder-debug" not in "".join(events)
    assert events[-1] == "prune:release:v9.9.9"


def test_upload_skips_unchanged_remote_objects(
    bunny: ModuleType, tmp_path: Path
) -> None:
    """Objects on Bunny with a matching SHA256 must not be re-PUT.

    Each rewrite can cold-start the edge cache for that path.
    """
    root = tmp_path / "upload"
    root.mkdir()
    same = b"same-payload"
    changed = b"new-payload"
    (root / "same.bin").write_bytes(same)
    (root / "changed.bin").write_bytes(changed)
    import hashlib

    remote = {
        "release/v1.0.0/same.bin": hashlib.sha256(same).hexdigest().upper(),
        "release/v1.0.0/changed.bin": "0" * 64,
    }
    puts: list[str] = []

    def fake_put(url, body, access_key, content_type, max_attempts=4):
        puts.append(url)

    with (
        patch.object(bunny, "put_file", side_effect=fake_put),
        patch.object(bunny, "_list_remote_checksums", return_value=remote),
        patch.object(bunny, "prune_other_versions"),
    ):
        code = bunny.upload_tree(
            root,
            "https://la.storage.bunnycdn.com/meshchatx",
            "key",
            "release/v1.0.0",
        )

    assert code == 0
    assert len(puts) == 1
    assert puts[0].endswith("/release/v1.0.0/changed.bin")


def test_upload_puts_metadata_last(bunny: ModuleType, tmp_path: Path) -> None:
    root = tmp_path / "upload"
    root.mkdir()
    (root / "checksums.txt").write_text("a  b\n", encoding="utf-8")
    (root / "MeshChatX.AppImage").write_bytes(b"big")
    (root / "MeshChatX.AppImage.sha256").write_text("x\n", encoding="utf-8")

    puts: list[str] = []

    def fake_put(url, body, access_key, content_type, max_attempts=4):
        puts.append(url.rsplit("/", 1)[-1])

    with (
        patch.object(bunny, "put_file", side_effect=fake_put),
        patch.object(bunny, "_list_remote_checksums", return_value={}),
        patch.object(bunny, "prune_other_versions"),
    ):
        bunny.upload_tree(
            root,
            "https://la.storage.bunnycdn.com/meshchatx",
            "key",
            "release/v1.0.0",
        )

    assert puts[0] == "MeshChatX.AppImage"
    assert puts[-1] in {"checksums.txt", "MeshChatX.AppImage.sha256"}
    assert puts.index("MeshChatX.AppImage") < puts.index("checksums.txt")


def test_put_file_retries_5xx(bunny: ModuleType) -> None:
    calls = {"n": 0}

    class FakeResp:
        def __enter__(self) -> FakeResp:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def getcode(self) -> int:
            return 201

    def fake_urlopen(req: Any, timeout: int = 0) -> Any:
        calls["n"] += 1
        if calls["n"] < 3:
            raise bunny.urllib.error.HTTPError(
                req.full_url,
                503,
                "unavailable",
                hdrs=None,
                fp=io.BytesIO(b"retry"),
            )
        return FakeResp()

    with (
        patch.object(bunny.urllib.request, "urlopen", side_effect=fake_urlopen),
        patch.object(bunny.time, "sleep", return_value=None),
    ):
        bunny.put_file(
            "https://example.test/obj",
            b"hi",
            "key",
            "application/octet-stream",
        )

    assert calls["n"] == 3
