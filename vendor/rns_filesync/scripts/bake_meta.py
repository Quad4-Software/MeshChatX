#!/usr/bin/env python3
"""Bake version, build date, and git commit into rns_filesync/_meta.py."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
META = ROOT / "rns_filesync" / "_meta.py"
PYPROJECT = ROOT / "pyproject.toml"

TEMPLATE = '''"""Package version and build metadata.

Values are overwritten by make meta / make build when building from git.
Defaults keep editable installs and tests working without a Makefile bake step.
"""

from __future__ import annotations

__version__ = {version!r}

BUILD_DATE = {build_date!r}

GIT_COMMIT = {commit!r}

GIT_DIRTY = {dirty!r}


def version_string() -> str:
    """Single-line version for CLI -v / --version."""
    parts = [f"rns-filesync {{__version__}}"]
    if BUILD_DATE and BUILD_DATE != "unknown":
        parts.append(f"built {{BUILD_DATE}}")
    if GIT_COMMIT and GIT_COMMIT != "unknown":
        dirty = "+" if GIT_DIRTY in {{"1", "true", "yes", "dirty"}} else ""
        parts.append(f"commit {{GIT_COMMIT}}{{dirty}}")
    return " | ".join(parts)


def version_info() -> dict[str, str]:
    return {{
        "version": __version__,
        "build_date": BUILD_DATE,
        "git_commit": GIT_COMMIT,
        "git_dirty": GIT_DIRTY,
    }}
'''


def _version() -> str:
    if "VERSION" in os.environ:
        return os.environ["VERSION"]
    try:
        import tomllib

        data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
        return str(data["project"]["version"])
    except Exception:
        from rns_filesync._meta import __version__

        return __version__


def _git_commit() -> str:
    if "GIT_COMMIT" in os.environ:
        return os.environ["GIT_COMMIT"]
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=ROOT,
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def _git_dirty() -> str:
    if "GIT_DIRTY" in os.environ:
        return os.environ["GIT_DIRTY"]
    try:
        subprocess.check_call(
            ["git", "diff", "--quiet"],
            cwd=ROOT,
            stderr=subprocess.DEVNULL,
        )
        return "0"
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "1"


def _build_date() -> str:
    if "BUILD_DATE" in os.environ:
        return os.environ["BUILD_DATE"]
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    version = _version()
    build_date = _build_date()
    commit = _git_commit()
    dirty = _git_dirty()
    META.write_text(
        TEMPLATE.format(
            version=version,
            build_date=build_date,
            commit=commit,
            dirty=dirty,
        ),
        encoding="utf-8",
    )
    print(f"Baked version={version} date={build_date} commit={commit} dirty={dirty}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
