# SPDX-License-Identifier: 0BSD

from pathlib import Path
from unittest.mock import patch

import meshchatx.android_codec2 as android_codec2


def test_ensure_codec2_skips_non_android():
    android_codec2._codec2_preload_done = False
    android_codec2._codec2_preload_error = None
    with patch.object(android_codec2, "_is_chaquopy_android", return_value=False):
        assert android_codec2.ensure_codec2_native_library() is True
        assert android_codec2.codec2_preload_error() is None


def test_ensure_codec2_loads_bundled_library(tmp_path):
    lib = tmp_path / "libcodec2.so"
    lib.write_bytes(b"\x7fELF")

    android_codec2._codec2_preload_done = False
    android_codec2._codec2_preload_error = None

    with (
        patch.object(android_codec2, "_is_chaquopy_android", return_value=True),
        patch.object(android_codec2.ctypes, "CDLL", side_effect=[OSError(), None]) as cdll,
        patch.object(
            android_codec2,
            "_libcodec2_candidates",
            return_value=[lib],
        ),
    ):
        assert android_codec2.ensure_codec2_native_library() is True
        cdll.assert_called_with(str(lib))


def test_repack_script_bundles_libcodec2(tmp_path):
    import importlib.util
    import zipfile

    repo_root = Path(__file__).resolve().parents[2]
    script = repo_root / "scripts" / "repack-android-pycodec2-wheels.py"
    spec = importlib.util.spec_from_file_location("repack_pycodec2", script)
    repack_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(repack_mod)
    repack_pycodec2_wheel = repack_mod.repack_pycodec2_wheel

    lib_wheel = tmp_path / "chaquopy_libcodec2-1.2.0-0-py3-none-android_24_arm64_v8a.whl"
    py_wheel = tmp_path / "pycodec2-4.1.1-0-cp311-cp311-android_24_arm64_v8a.whl"

    with zipfile.ZipFile(lib_wheel, "w") as zout:
        zout.writestr("chaquopy/lib/libcodec2.so", b"\x7fELF-lib")

    record = (
        "pycodec2/pycodec2.so,sha256=deadbeef,8\n"
        "pycodec2.dist-info/METADATA,sha256=deadbeef,4\n"
        "pycodec2.dist-info/RECORD,,\n"
    )
    with zipfile.ZipFile(py_wheel, "w") as zout:
        zout.writestr("pycodec2/pycodec2.so", b"\x7fELF-mod")
        zout.writestr("pycodec2.dist-info/METADATA", b"meta")
        zout.writestr("pycodec2.dist-info/RECORD", record)

    lib_src = tmp_path / "libcodec2.so"
    lib_src.write_bytes(b"\x7fELF-lib")
    assert repack_pycodec2_wheel(py_wheel, lib_src)

    with zipfile.ZipFile(py_wheel) as zin:
        names = zin.namelist()
        record_text = zin.read("pycodec2.dist-info/RECORD").decode()
    assert "pycodec2/libcodec2.so" in names
    assert ",,\n" not in record_text
    for line in record_text.splitlines():
        if not line.strip():
            continue
        size_field = line.rsplit(",", 1)[-1]
        assert size_field
        int(size_field)
