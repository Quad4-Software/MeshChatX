# SPDX-License-Identifier: 0BSD

"""Oracle checks for git-log release changelog notes."""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_CHANGELOG = _REPO / "scripts" / "ci" / "github-release-changelog.sh"
_DRAFT = _REPO / "scripts" / "ci" / "github-draft-release-upload-assets.sh"

_BULLET_RE = re.compile(r"^\* ([0-9a-f]{40}) (.+)\.$")


def _run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=_REPO,
        text=True,
        capture_output=True,
        check=True,
        **kwargs,
    )


def test_changelog_script_exists_and_is_executable():
    assert _CHANGELOG.is_file()
    assert os.access(_CHANGELOG, os.X_OK)


def test_changelog_script_bash_syntax():
    subprocess.run(["bash", "-n", str(_CHANGELOG)], check=True, cwd=_REPO)  # nosec: BAN-B607


def test_draft_script_invokes_changelog_helper():
    text = _DRAFT.read_text(encoding="utf-8")
    assert "github-release-changelog.sh" in text
    assert "MESHCHATX_DRAFT_NOTES_ONLY" in text


def test_changelog_v4_8_5_uses_prior_stable_and_full_sha_bullets():
    tags = {
        t.strip()
        for t in _run(["git", "tag", "-l", "v4.8.4", "v4.8.5"]).stdout.splitlines()
    }
    if tags != {"v4.8.4", "v4.8.5"}:
        # Shallow clones in some CI shards may lack tags.
        subprocess.run(  # nosec: BAN-B607
            ["git", "fetch", "--tags", "--depth", "50", "origin"],
            cwd=_REPO,
            check=False,
            capture_output=True,
            text=True,
        )
        tags = {
            t.strip()
            for t in _run(["git", "tag", "-l", "v4.8.4", "v4.8.5"]).stdout.splitlines()
        }
    if tags != {"v4.8.4", "v4.8.5"}:
        import pytest

        pytest.skip("v4.8.4/v4.8.5 tags not available in this clone")

    out = _run(["bash", str(_CHANGELOG), "v4.8.5"]).stdout
    assert out.startswith("## Changelog\n")
    bullets = [ln for ln in out.splitlines() if ln.startswith("* ")]
    assert bullets, "expected at least one changelog bullet"
    for ln in bullets:
        m = _BULLET_RE.match(ln)
        assert m, ln
        subject = m.group(2)
        assert not subject.startswith("docs:")
        assert not subject.startswith("test:")
        assert not subject.startswith("ci:")

    # Previous baseline for a stable tag must be the prior vN tag, not a nightly.
    prev = _run(
        [
            "git",
            "describe",
            "--tags",
            "--abbrev=0",
            "--match",
            "v[0-9]*",
            "--exclude",
            "v4.8.5",
            "v4.8.5^",
        ]
    ).stdout.strip()
    assert prev == "v4.8.4"

    # Every listed commit must be in v4.8.4..v4.8.5.
    range_shas = set(
        _run(["git", "rev-list", "--no-merges", "v4.8.4..v4.8.5"]).stdout.split()
    )
    for ln in bullets:
        sha = _BULLET_RE.match(ln).group(1)
        assert sha in range_shas, sha


def test_draft_notes_only_includes_changelog_then_checksums():
    with tempfile.TemporaryDirectory() as tmp:
        asset = Path(tmp) / "dummy-asset.bin"
        asset.write_bytes(b"meshchatx-release-notes-oracle\n")
        env = os.environ.copy()
        env["MESHCHATX_DRAFT_NOTES_ONLY"] = "1"
        env["TAG"] = "v4.8.5"
        env.pop("GH_TOKEN", None)
        proc = subprocess.run(  # nosec: BAN-B607
            ["bash", str(_DRAFT), tmp],
            cwd=_REPO,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        if proc.returncode != 0 and "unknown tag" in (proc.stderr or ""):
            import pytest

            pytest.skip("v4.8.5 tag not available in this clone")
        assert proc.returncode == 0, proc.stderr
        body = proc.stdout
        assert "## Changelog" in body
        assert "## SHA256 Checksums" in body
        assert "## Verification" in body
        assert "dummy-asset.bin" in body
        assert body.index("## Changelog") < body.index("## SHA256 Checksums")
        assert body.index("## SHA256 Checksums") < body.index("## Verification")
        # Bullet shape: full sha, subject, trailing period.
        if "* " in body:
            assert re.search(r"\* [0-9a-f]{40} .+\.", body)
