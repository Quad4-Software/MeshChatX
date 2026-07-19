# SPDX-License-Identifier: 0BSD

import os

from meshchatx.src.path_utils import safe_path_under_dir


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
