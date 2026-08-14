# SPDX-License-Identifier: 0BSD

import os
import zipfile

from meshchatx.src.backend.database import _zip_write_file


def test_zip_write_file_clamps_pre_1980_mtime(tmp_path):
    old_file = tmp_path / "legacy.dat"
    old_file.write_bytes(b"legacy")
    os.utime(old_file, (0, 0))

    zip_path = tmp_path / "backup.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        _zip_write_file(zf, str(old_file), arcname="legacy.dat")

    with zipfile.ZipFile(zip_path, "r") as zf:
        info = zf.getinfo("legacy.dat")
        assert info.date_time[0] >= 1980
        assert zf.read("legacy.dat") == b"legacy"
