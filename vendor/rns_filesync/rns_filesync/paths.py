"""Path jail helpers for sync directory confinement."""

from __future__ import annotations

import os


class PathJailError(ValueError):
    """Raised when a path escapes the sync root."""


def normalize_relpath(relpath: str) -> str:
    """Normalize a relative path for protocol use.

    Raises:
        PathJailError: If the path is empty, absolute, or contains null bytes.

    """
    if not isinstance(relpath, str) or not relpath or "\x00" in relpath:
        raise PathJailError("invalid relative path")
    # Reject Windows drive / UNC style paths even on POSIX.
    if relpath.startswith(("/", "\\")) or os.path.isabs(relpath):
        raise PathJailError("absolute paths are not allowed")
    if len(relpath) >= 2 and relpath[1] == ":":
        raise PathJailError("absolute paths are not allowed")
    if relpath.startswith("\\\\") or relpath.startswith("//"):
        raise PathJailError("absolute paths are not allowed")

    cleaned = os.path.normpath(relpath.replace("\\", "/"))
    if cleaned in (".", ""):
        raise PathJailError("empty relative path")
    parts = cleaned.split("/")
    if any(part in ("", "..") for part in parts):
        raise PathJailError("path escape attempt")
    if cleaned.startswith("../") or cleaned == "..":
        raise PathJailError("path escape attempt")
    # Disallow hidden protocol/control filenames under sync root.
    if any(
        part == ".rns-filesync.db" or part.startswith(".rns-xfer-") for part in parts
    ):
        raise PathJailError("reserved path")
    return cleaned


def resolve_under_root(root: str, relpath: str) -> str:
    """Resolve relpath under root and ensure it stays jailed.

    Returns:
        Absolute real path under root.

    Raises:
        PathJailError: If resolution escapes root.

    """
    root_real = os.path.realpath(root)
    safe_rel = normalize_relpath(relpath)
    candidate = os.path.realpath(os.path.join(root_real, safe_rel))
    if candidate != root_real and not candidate.startswith(root_real + os.sep):
        raise PathJailError("path escapes sync root")
    return candidate


def relative_to_root(root: str, abspath: str) -> str:
    """Return a jailed relative path from an absolute path under root."""
    root_real = os.path.realpath(root)
    path_real = os.path.realpath(abspath)
    if path_real != root_real and not path_real.startswith(root_real + os.sep):
        raise PathJailError("path escapes sync root")
    rel = os.path.relpath(path_real, root_real)
    return normalize_relpath(rel)
