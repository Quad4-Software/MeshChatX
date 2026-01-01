"""Update project version references to stay aligned with the Electron build.

Reads `package.json`, writes the same version into `src/version.py`, and
updates the `[tool.poetry] version` field inside `pyproject.toml`. Run this
before any Python packaging commands so the wheel version matches the
Electron artifacts.
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_JSON = ROOT / "package.json"
VERSION_PY = ROOT / "meshchatx" / "src" / "version.py"
PYPROJECT_TOML = ROOT / "pyproject.toml"


def read_package_version() -> str:
    with PACKAGE_JSON.open() as handle:
        return json.load(handle)["version"]


def write_version_module(version: str) -> None:
    content = (
        '"""\n'
        "Auto-generated helper so Python tooling and the Electron build\n"
        "share the same version string.\n"
        '"""\n\n'
        f"__version__ = {version!r}\n"
    )
    if VERSION_PY.exists() and VERSION_PY.read_text() == content:
        return
    VERSION_PY.write_text(content)


def update_poetry_version(version: str) -> None:
    if not PYPROJECT_TOML.exists():
        return
    content = PYPROJECT_TOML.read_text()

    def replacer(match):
        return f"{match.group(1)}{version}{match.group(2)}"

    new_content, replaced = re.subn(
        r'(?m)^(version\s*=\s*")[^"]*(")',
        replacer,
        content,
        count=1,
    )
    if replaced == 0:
        msg = "failed to update version in pyproject.toml"
        raise RuntimeError(msg)
    if new_content != content:
        PYPROJECT_TOML.write_text(new_content)


def main() -> None:
    version = read_package_version()
    write_version_module(version)
    update_poetry_version(version)


if __name__ == "__main__":
    main()
