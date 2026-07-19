"""Package version and build metadata.

Values are overwritten by make meta / make build when building from git.
Defaults keep editable installs and tests working without a Makefile bake step.
"""

from __future__ import annotations

__version__ = '1.0.0'

BUILD_DATE = '2026-07-19T13:14:52Z'

GIT_COMMIT = '12161f3'

GIT_DIRTY = '1'


def version_string() -> str:
    """Single-line version for CLI -v / --version."""
    parts = [f"rns-filesync {__version__}"]
    if BUILD_DATE and BUILD_DATE != "unknown":
        parts.append(f"built {BUILD_DATE}")
    if GIT_COMMIT and GIT_COMMIT != "unknown":
        dirty = "+" if GIT_DIRTY in {"1", "true", "yes", "dirty"} else ""
        parts.append(f"commit {GIT_COMMIT}{dirty}")
    return " | ".join(parts)


def version_info() -> dict[str, str]:
    return {
        "version": __version__,
        "build_date": BUILD_DATE,
        "git_commit": GIT_COMMIT,
        "git_dirty": GIT_DIRTY,
    }
