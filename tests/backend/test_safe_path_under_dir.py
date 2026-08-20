# SPDX-License-Identifier: 0BSD

import os
from unittest.mock import patch

import pytest

from meshchatx.src.path_utils import (
    atomic_write_bytes,
    atomic_write_text,
    safe_path_under_dir,
)


def test_safe_path_under_dir_accepts_basename(tmp_path):
    target = tmp_path / "rec.opus"
    target.write_bytes(b"x")
    out = safe_path_under_dir(str(tmp_path), "rec.opus")
    assert out == os.path.realpath(str(target))


def test_safe_path_under_dir_collapses_traversal_to_basename(tmp_path):
    out = safe_path_under_dir(str(tmp_path), "../evil.opus")
    assert out == os.path.realpath(os.path.join(str(tmp_path), "evil.opus"))


def test_safe_path_under_dir_rejects_nul_and_dot(tmp_path):
    assert safe_path_under_dir(str(tmp_path), "a\x00b.opus") is None
    assert safe_path_under_dir(str(tmp_path), "..") is None
    assert safe_path_under_dir(str(tmp_path), "") is None


def test_safe_path_under_dir_rejects_symlink_escape(tmp_path):
    """Reject basename symlinks whose real path leaves the jail."""
    outside = tmp_path / "outside.secret"
    outside.write_bytes(b"secret")
    jail = tmp_path / "jail"
    jail.mkdir()
    link = jail / "escape.opus"
    link.symlink_to(outside)
    assert safe_path_under_dir(str(jail), "escape.opus") is None


def test_atomic_write_bytes_keeps_destination_if_tmp_write_fails(tmp_path):
    dest = tmp_path / "meta.json"
    dest.write_bytes(b"OLD")
    with patch("os.fdopen", side_effect=OSError("disk full")):
        with pytest.raises(OSError, match="disk full"):
            atomic_write_bytes(str(dest), b"NEW")
    assert dest.read_bytes() == b"OLD"


def test_atomic_write_text_replaces_destination(tmp_path):
    dest = tmp_path / "meta.json"
    dest.write_text("OLD", encoding="utf-8")
    atomic_write_text(str(dest), "NEW")
    assert dest.read_text(encoding="utf-8") == "NEW"


def test_atomic_write_text_accepts_path(tmp_path):
    dest = tmp_path / "meta.json"
    atomic_write_text(dest, "via-path")
    assert dest.read_text(encoding="utf-8") == "via-path"
