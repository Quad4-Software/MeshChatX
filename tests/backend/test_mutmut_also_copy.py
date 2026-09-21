# SPDX-License-Identifier: 0BSD

"""mutmut mutants/ must include meshchatx modules outside src/backend."""

from __future__ import annotations

import tomllib
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def _mutmut_config() -> dict:
    data = tomllib.loads((_root() / "pyproject.toml").read_text(encoding="utf-8"))
    return data["tool"]["mutmut"]


def _also_copy_covers(rel: Path, also_copy: list[str]) -> bool:
    rel_s = rel.as_posix()
    for item in also_copy:
        normalized = item.rstrip("/")
        if rel_s == item or rel_s == normalized:
            return True
        if rel_s.startswith(normalized + "/"):
            return True
    return False


def test_mutmut_also_copy_covers_package_modules_outside_backend():
    also_copy = list(_mutmut_config().get("also_copy", []))
    root = _root()
    required = sorted(
        path
        for path in (
            list((root / "meshchatx").glob("*.py"))
            + list((root / "meshchatx" / "src").glob("*.py"))
        )
        if path.name != "_build_meta_baked.py"
    )
    missing = [
        path.relative_to(root).as_posix()
        for path in required
        if not _also_copy_covers(path.relative_to(root), also_copy)
    ]
    assert missing == []


# Repo-relative inputs that backend tests read while running inside mutants/.
# pytest.ini is load-bearing: without it pytest-asyncio loses asyncio_mode=auto
# and marker registration inside the replica.
_REQUIRED_REPO_PATHS = [
    "pytest.ini",
    "package.json",
    "cx_setup.py",
    "Taskfile.yml",
    ".agents/module-ownership.md",
    ".github/workflows/ci.yml",
    ".github/workflows/build-release.yml",
    ".github/workflows/native-build-dev.yml",
    "android/app/build.gradle",
    "android/app/src/main/java/org/able/BLE.java",
    "electron/app-version.json",
    "packaging/arch/PKGBUILD",
    "packaging/arch/.SRCINFO",
    "scripts/sync-issues.py",
    "scripts/ci/tree-manifest.sh",
    "scripts/ci/tree_manifest_generate.py",
    "scripts/ci/github-release-changelog.sh",
    "scripts/ci/github-draft-release-upload-assets.sh",
    "typings",
    "meshchatx/src/frontend/features",
    "meshchatx/src/frontend/js",
]


def test_mutmut_also_copy_covers_repo_paths_tests_read():
    also_copy = list(_mutmut_config().get("also_copy", []))
    root = _root()
    missing_on_disk = [rel for rel in _REQUIRED_REPO_PATHS if not (root / rel).exists()]
    assert missing_on_disk == []
    uncovered = [
        rel
        for rel in _REQUIRED_REPO_PATHS
        if not _also_copy_covers(Path(rel), also_copy)
    ]
    assert uncovered == []
