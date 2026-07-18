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
