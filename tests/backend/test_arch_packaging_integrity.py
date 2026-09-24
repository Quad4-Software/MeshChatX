# SPDX-License-Identifier: 0BSD

"""PKGBUILD sha256sums must match local source files and .SRCINFO."""

from __future__ import annotations

import hashlib
import re
import shlex
from pathlib import Path

ARCH_DIR = Path(__file__).resolve().parents[2] / "packaging" / "arch"

_VCS_PREFIX = re.compile(r"^(bzr|fossil|git|hg|svn)\+")


def _pkgbuild_array(text: str, name: str) -> list[str]:
    match = re.search(rf"^{name}=\((.*?)\)", text, re.DOTALL | re.MULTILINE)
    assert match, f"PKGBUILD is missing a {name} array"
    return shlex.split(match.group(1))


def _local_filename(entry: str) -> str | None:
    target = entry.split("::", 1)[-1]
    if "://" in target or _VCS_PREFIX.match(target):
        return None
    return target


def _pkgbuild_and_sums() -> tuple[list[str], list[str]]:
    text = (ARCH_DIR / "PKGBUILD").read_text(encoding="utf-8")
    sources = _pkgbuild_array(text, "source")
    sums = _pkgbuild_array(text, "sha256sums")
    assert len(sources) == len(sums), (
        f"PKGBUILD source has {len(sources)} entries but "
        f"sha256sums has {len(sums)}"
    )
    return sources, sums


def test_pkgbuild_sha256sums_match_local_source_files():
    sources, sums = _pkgbuild_and_sums()
    for entry, expected in zip(sources, sums):
        filename = _local_filename(entry)
        if filename is None:
            continue
        path = ARCH_DIR / filename
        assert path.is_file(), f"PKGBUILD source {filename!r} is missing on disk"
        assert expected != "SKIP", (
            f"local source {filename!r} must not use SKIP in sha256sums"
        )
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        assert actual == expected, (
            f"sha256sums entry for {filename!r} is stale: PKGBUILD has "
            f"{expected}, file hashes to {actual}. Run updpkgsums in "
            f"packaging/arch/ and regenerate .SRCINFO."
        )


def test_srcinfo_sha256sums_match_pkgbuild():
    _, sums = _pkgbuild_and_sums()
    srcinfo = (ARCH_DIR / ".SRCINFO").read_text(encoding="utf-8")
    srcinfo_sums = re.findall(r"^\tsha256sums = (.+)$", srcinfo, re.MULTILINE)
    assert srcinfo_sums == sums, (
        ".SRCINFO sha256sums are out of sync with PKGBUILD. Regenerate with "
        "makepkg --printsrcinfo > .SRCINFO in packaging/arch/."
    )
