# SPDX-License-Identifier: 0BSD

import json
import re
from pathlib import Path

import pytest

import meshchatx

ROOT = Path(__file__).resolve().parent.parent


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def package_version() -> str:
    return json.loads(read("package.json"))["version"]


def _first(pattern: str, rel: str) -> str:
    match = re.search(pattern, read(rel), re.MULTILINE)
    assert match, f"no match for {pattern!r} in {rel}"
    return match.group(1)


def _py_dunder_version(rel: str) -> list[str]:
    return [_first(r'^__version__\s*=\s*"([^"]+)"', rel)]


def _json_version(rel: str) -> list[str]:
    return [json.loads(read(rel))["version"]]


def _windows_info_json(rel: str) -> list[str]:
    data = json.loads(read(rel))
    return [data["fixed"]["file_version"], data["info"]["0000"]["ProductVersion"]]


def _plist_versions(rel: str) -> list[str]:
    text = read(rel)
    found = []
    for key in ("CFBundleVersion", "CFBundleShortVersionString"):
        match = re.search(rf"<key>{key}</key>\s*<string>([^<]+)</string>", text)
        assert match, f"no {key} in {rel}"
        found.append(match.group(1))
    return found


EXTRACTORS = {
    "pyproject.toml": lambda rel: [_first(r'^version\s*=\s*"([^"]+)"', rel)],
    "meshchatx/__init__.py": _py_dunder_version,
    "meshchatx/src/version.py": _py_dunder_version,
    "desktop/app-version.json": _json_version,
    "desktop/build/config.yml": lambda rel: [_first(r'^  version:\s*"([^"]+)"', rel)],
    "desktop/build/linux/nfpm/nfpm.yaml": lambda rel: [
        _first(r'^version:\s*"([^"]+)"', rel)
    ],
    "desktop/build/windows/info.json": _windows_info_json,
    "desktop/build/windows/wails.exe.manifest": lambda rel: [
        _first(r'name="com\.meshchatx\.app" version="([^"]+)"', rel)
    ],
    "desktop/build/windows/nsis/wails_tools.nsh": lambda rel: [
        _first(r'!define INFO_PRODUCTVERSION "([^"]+)"', rel)
    ],
    "desktop/build/darwin/Info.plist": _plist_versions,
    "desktop/build/darwin/Info.dev.plist": _plist_versions,
    "helm/meshchatx/Chart.yaml": lambda rel: [_first(r'^appVersion:\s*"([^"]+)"', rel)],
}


def test_meshchatx_version_is_semver_like():
    assert isinstance(meshchatx.__version__, str)
    assert re.match(r"^\d+\.\d+\.\d+", meshchatx.__version__)


@pytest.mark.parametrize("rel", sorted(EXTRACTORS), ids=sorted(EXTRACTORS))
def test_version_matches_package_json(rel: str):
    expected = package_version()
    for found in EXTRACTORS[rel](rel):
        assert found == expected, f"{rel}: found {found!r}, expected {expected!r}"


def test_android_gradle_version():
    expected = package_version()
    rel = "android/app/build.gradle"
    version_name = _first(r'versionName\s+"([^"]+)"', rel)
    assert version_name == expected, (
        f"{rel}: versionName {version_name!r} != {expected!r}"
    )

    major, minor, patch = (int(part) for part in expected.split(".")[:3])
    expected_code = major * 10000 + minor * 1000 + patch
    version_code = int(_first(r"versionCode\s+(\d+)", rel))
    assert version_code == expected_code, (
        f"{rel}: versionCode {version_code} != {expected_code} "
        f"(major*10000+minor*1000+patch for {expected})"
    )
