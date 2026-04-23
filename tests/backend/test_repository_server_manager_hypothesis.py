# SPDX-License-Identifier: 0BSD

"""Property tests for repository upload filename sanitization."""

import os
import re
import tempfile

from hypothesis import given, settings
from hypothesis import strategies as st

from meshchatx.src.backend.repository_server_manager import (
    RepositoryServerManager,
    _safe_any_upload_filename,
)

_SAFE_RE = re.compile(r"[A-Za-z0-9._+\-]+")


@settings(max_examples=250, deadline=None)
@given(name=st.text(max_size=400))
def test_safe_any_upload_filename_never_raises(name):
    out = _safe_any_upload_filename(name)
    if out is None:
        return
    assert isinstance(out, str)
    assert out == os.path.basename(name)
    assert out == name
    assert ".." not in out
    assert _SAFE_RE.fullmatch(out)


@settings(max_examples=200, deadline=None)
@given(
    base=st.from_regex(r"[A-Za-z0-9._+\-]{1,120}", fullmatch=True).filter(
        lambda b: b not in (".", "..") and ".." not in b
    ),
)
def test_save_upload_roundtrip_for_generated_safe_names(base):
    with tempfile.TemporaryDirectory() as td:
        mgr = RepositoryServerManager(td)
        ok, err = mgr.save_upload(base, b"\x00\x01\x02")
        assert ok and err is None
        dest = os.path.join(td, "repository-server", "uploads", base)
        assert dest == os.path.realpath(dest)
        assert os.path.isfile(dest)
        assert os.path.dirname(dest) == os.path.join(td, "repository-server", "uploads")


@settings(max_examples=120, deadline=None)
@given(
    prefix=st.text(max_size=80),
    base=st.from_regex(r"[A-Za-z0-9._+\-]{1,40}", fullmatch=True),
)
def test_save_upload_rejects_path_traversal_prefix(prefix, base):
    poison = prefix + "../" + base
    with tempfile.TemporaryDirectory() as td:
        mgr = RepositoryServerManager(td)
        ok, err = mgr.save_upload(poison, b"x")
        assert not ok
