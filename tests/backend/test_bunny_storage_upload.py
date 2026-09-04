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
        {"IsDirectory": True, "ObjectName": "v1.0.0"},
        {"IsDirectory": True, "ObjectName": "v1.1.0"},
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
        )

    assert len(deleted) == 1
    assert deleted[0].endswith("/release/v1.0.0")
    assert "v1.1.0" not in deleted[0]


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
