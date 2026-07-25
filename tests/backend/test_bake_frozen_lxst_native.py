# SPDX-License-Identifier: 0BSD

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from meshchatx.src.backend.bake_frozen_lxst_native import bake_lxst_filterlib


def test_bake_lxst_filterlib_prunes_alien_blobs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lxst = tmp_path / "lib" / "LXST"
    lxst.mkdir(parents=True)
    (lxst / "filterlib.dll").write_bytes(b"win")
    (lxst / "filterlib.cpython-314-x86_64-linux-gnu.so").write_bytes(b"linux")

    monkeypatch.setattr(sys, "platform", "win32", raising=False)
    monkeypatch.setattr(
        "meshchatx.src.backend.bake_frozen_lxst_native.sysconfig.get_config_var",
        lambda name: ".cp314-win_amd64.pyd" if name == "EXT_SUFFIX" else None,
    )

    bake_lxst_filterlib(tmp_path)

    assert (lxst / "filterlib.dll").is_file()
    assert not (lxst / "filterlib.cpython-314-x86_64-linux-gnu.so").exists()
