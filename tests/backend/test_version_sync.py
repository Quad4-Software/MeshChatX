# SPDX-License-Identifier: 0BSD

"""Synced version files must match package.json after pnpm run version:sync."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _package_version() -> str:
    version = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))["version"]
    assert isinstance(version, str) and re.match(r"^\d+\.\d+\.\d+", version)
    return version


def _text(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_electron_app_version_json_matches_package():
    data = json.loads(_text("electron/app-version.json"))
    assert data["version"] == _package_version()


def test_python_version_strings_match_package():
    version = _package_version()
    expected = f'__version__ = "{version}"'
    assert expected in _text("meshchatx/__init__.py")
    assert expected in _text("meshchatx/src/version.py")


def test_pyproject_version_matches_package():
    assert re.search(
        rf'^version = "{re.escape(_package_version())}"',
        _text("pyproject.toml"),
        re.MULTILINE,
    )


def test_android_version_matches_package():
    version = _package_version()
    major, minor, patch = (int(part) for part in version.split(".")[:3])
    version_code = major * 10000 + minor * 1000 + patch
    gradle = _text("android/app/build.gradle")
    assert f'versionName "{version}"' in gradle
    assert f"versionCode {version_code}" in gradle


def test_notices_and_backend_license_match_package():
    version = _package_version()
    notices = _text("meshchatx/src/backend/data/THIRD_PARTY_NOTICES.txt")
    assert re.search(
        rf"^reticulum-meshchatx {re.escape(version)}$", notices, re.MULTILINE
    )
    licenses = json.loads(_text("meshchatx/src/backend/data/licenses_backend.json"))
    entry = next(item for item in licenses if item.get("name") == "reticulum-meshchatx")
    assert entry["version"] == version


def test_arch_packaging_version_matches_package():
    version = _package_version()
    pkgbuild = _text("packaging/arch/PKGBUILD")
    assert re.search(rf"^pkgver={re.escape(version)}", pkgbuild, re.MULTILINE)
    assert f'printf "{version}.r%s.%s"' in pkgbuild
    srcinfo = _text("packaging/arch/.SRCINFO")
    assert re.search(rf"^\tpkgver = {re.escape(version)}", srcinfo, re.MULTILINE)
