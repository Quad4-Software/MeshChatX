# SPDX-License-Identifier: 0BSD

"""Oracle checks for Android GitHub release APK naming."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_SCRIPT = _REPO / "scripts" / "ci" / "stage-android-release-apks.sh"
_GRADLE = _REPO / "android" / "app" / "build.gradle"
_WORKFLOW = _REPO / ".github" / "workflows" / "android-apk-tag.yml"


def test_stage_script_exists_and_is_executable():
    assert _SCRIPT.is_file()
    assert os.access(_SCRIPT, os.X_OK)


def test_stage_script_bash_syntax():
    subprocess.run(["bash", "-n", str(_SCRIPT)], check=True)  # nosec: BAN-B607


def test_gradle_release_apk_uses_desktop_asset_prefix():
    text = _GRADLE.read_text(encoding="utf-8")
    assert '? "-universal"' in text
    assert (
        "ReticulumMeshChatX-v${variant.versionName}-android${abiSuffix}-unsigned.apk"
        in text
    )
    assert "app-release-unsigned.apk" not in text


def test_workflow_stages_with_rename_script():
    text = _WORKFLOW.read_text(encoding="utf-8")
    assert "scripts/ci/stage-android-release-apks.sh" in text
    assert 'cp -v "${signed[@]}" android-apks-for-draft/' not in text


def test_stage_renames_signed_apk_to_desktop_scheme(tmp_path: Path):
    src = tmp_path / "release"
    dest = tmp_path / "draft"
    src.mkdir()
    (src / "ReticulumMeshChatX-v4.8.4-android-universal-signed.apk").write_bytes(b"apk")
    (src / "ReticulumMeshChatX-v4.8.4-android-arm64-v8a-signed.apk").write_bytes(b"apk")
    proc = subprocess.run(  # nosec: BAN-B607
        ["bash", str(_SCRIPT), str(src), str(dest)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    names = sorted(p.name for p in dest.iterdir())
    assert names == [
        "ReticulumMeshChatX-v4.8.4-android-arm64-v8a.apk",
        "ReticulumMeshChatX-v4.8.4-android-universal.apk",
    ]


def test_stage_rejects_missing_universal_or_abi_tag(tmp_path: Path):
    src = tmp_path / "release"
    dest = tmp_path / "draft"
    src.mkdir()
    (src / "ReticulumMeshChatX-v4.8.4-android-signed.apk").write_bytes(b"apk")
    proc = subprocess.run(  # nosec: BAN-B607
        ["bash", str(_SCRIPT), str(src), str(dest)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode != 0
    assert "ReticulumMeshChatX-v*-android-universal.apk" in proc.stderr
    assert not dest.exists() or not any(dest.iterdir())


def test_stage_rejects_gradle_default_app_release_signed(tmp_path: Path):
    src = tmp_path / "release"
    dest = tmp_path / "draft"
    src.mkdir()
    (src / "app-release-signed.apk").write_bytes(b"apk")
    proc = subprocess.run(  # nosec: BAN-B607
        ["bash", str(_SCRIPT), str(src), str(dest)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode != 0
    assert "ReticulumMeshChatX-v*-android-universal.apk" in proc.stderr
    assert not dest.exists() or not any(dest.iterdir())


def test_stage_fails_when_no_signed_apk(tmp_path: Path):
    src = tmp_path / "release"
    dest = tmp_path / "draft"
    src.mkdir()
    (src / "ReticulumMeshChatX-v4.8.4-android-universal-unsigned.apk").write_bytes(
        b"apk",
    )
    proc = subprocess.run(  # nosec: BAN-B607
        ["bash", str(_SCRIPT), str(src), str(dest)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode != 0
    assert "Expected *-signed.apk" in proc.stderr
