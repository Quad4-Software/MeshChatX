# SPDX-License-Identifier: 0BSD
"""Contract tests for the Flatpak build and publish branch handling.

A bundle built without an explicit OSTree branch exports ``master``. The
publish step only accepts the channel branch, so a v-tag release published
nothing to the Flatpak remote while the rest of the release succeeded.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "scripts" / "ci" / "github-build-linux-flatpak.sh"
EXPORT = ROOT / "scripts" / "ci" / "github-flatpak-ostree-export.sh"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_build_passes_default_branch_to_flatpak_builder() -> None:
    text = _read(BUILD)
    match = re.search(r"^flatpak-builder [^\n]*", text, re.MULTILINE)
    assert match, "flatpak-builder invocation not found"
    line = match.group(0)
    assert '--default-branch="${branch}"' in line, line


def test_build_passes_branch_to_build_bundle() -> None:
    text = _read(BUILD)
    match = re.search(r"^flatpak build-bundle [^\n]*", text, re.MULTILINE)
    assert match, "flatpak build-bundle invocation not found"
    line = match.group(0)
    assert '"${branch}"' in line, line


def test_build_validates_branch_before_export() -> None:
    text = _read(BUILD)
    assert "testing | beta | stable" in text


def test_publish_expects_channel_ref() -> None:
    text = _read(EXPORT)
    assert 'target_ref="app/${appid}/${arch}/${branch}"' in text
    assert "Expected ${target_ref} after import" in text
