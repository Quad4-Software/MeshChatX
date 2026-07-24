# SPDX-License-Identifier: 0BSD

from pathlib import Path
from unittest.mock import patch

import pytest

from meshchatx import android_codec2


def test_ensure_codec2_skips_non_android():
    android_codec2.reset_codec2_preload_state_for_tests()
    with patch.object(android_codec2, "_is_chaquopy_android", return_value=False):
        assert android_codec2.ensure_codec2_native_library() is True
        assert android_codec2.codec2_preload_error() is None


def test_ensure_codec2_loads_bundled_library(tmp_path):
    lib = tmp_path / "libcodec2.so"
    lib.write_bytes(b"\x7fELF")

    android_codec2.reset_codec2_preload_state_for_tests()

    with (
        patch.object(android_codec2, "_is_chaquopy_android", return_value=True),
        patch.object(android_codec2, "_java_system_load_library", return_value=False),
        patch.object(
            android_codec2,
            "_cdll_load",
            side_effect=[OSError(), None],
        ) as cdll,
        patch.object(
            android_codec2,
            "_libcodec2_candidates",
            return_value=[lib],
        ),
    ):
        assert android_codec2.ensure_codec2_native_library() is True
        assert cdll.call_count == 2
        assert cdll.call_args_list[0].args[0] == "libcodec2.so"
        assert cdll.call_args_list[1].args[0] == str(lib)


def test_ensure_codec2_prefers_java_load_library():
    android_codec2.reset_codec2_preload_state_for_tests()
    with (
        patch.object(android_codec2, "_is_chaquopy_android", return_value=True),
        patch.object(android_codec2, "_java_system_load_library", return_value=True) as java_load,
        patch.object(android_codec2, "_cdll_load") as cdll,
    ):
        assert android_codec2.ensure_codec2_native_library() is True
        java_load.assert_called_once_with("codec2")
        cdll.assert_not_called()
        assert android_codec2.codec2_preload_error() is None


def test_libcodec2_candidates_find_without_importing_pycodec2(tmp_path, monkeypatch):
    """Discovery must not import pycodec2 (extension needs libcodec2 already loaded)."""
    site = tmp_path / "site-packages"
    pkg = site / "pycodec2"
    pkg.mkdir(parents=True)
    lib = pkg / "libcodec2.so"
    lib.write_bytes(b"\x7fELF")
    monkeypatch.syspath_prepend(str(site))

    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "pycodec2" or name.startswith("pycodec2."):
            raise ImportError("pycodec2 must not be imported during candidate search")
        return real_import(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=fake_import):
        candidates = android_codec2._libcodec2_candidates()

    assert lib.resolve() in [c.resolve() for c in candidates]


def test_probe_pycodec2_reports_failure_when_import_breaks():
    android_codec2.reset_codec2_preload_state_for_tests()
    android_codec2._codec2_preload_done = True
    android_codec2._codec2_preload_error = None
    with (
        patch.object(android_codec2, "_is_chaquopy_android", return_value=False),
        patch.dict("sys.modules", {"pycodec2": None}),
    ):
        import builtins

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "pycodec2":
                raise ImportError("no pycodec2")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=fake_import):
            ok, err = android_codec2.probe_pycodec2()
        assert ok is False
        assert err


def test_vendor_wheels_bundle_libcodec2_for_all_abis():
    import zipfile

    repo = Path(__file__).resolve().parents[2]
    vendor = repo / "android" / "vendor"
    if not vendor.is_dir():
        pytest.skip("android/vendor not present (gitignored)")
    abis = ("arm64_v8a", "armeabi_v7a", "x86_64")
    for abi in abis:
        wheels = sorted(vendor.glob(f"pycodec2-*-android_24_{abi}.whl"))
        if not wheels:
            pytest.skip(f"missing pycodec2 wheel for {abi}")
        with zipfile.ZipFile(wheels[-1]) as zin:
            assert "pycodec2/libcodec2.so" in zin.namelist()
            assert "pycodec2/pycodec2.so" in zin.namelist()
        lib_wheels = sorted(vendor.glob(f"chaquopy_libcodec2-*-android_24_{abi}.whl"))
        if not lib_wheels:
            pytest.skip(f"missing chaquopy_libcodec2 for {abi}")
        with zipfile.ZipFile(lib_wheels[-1]) as zin:
            assert "chaquopy/lib/libcodec2.so" in zin.namelist()


def test_jni_libs_synced_for_all_abis():
    repo = Path(__file__).resolve().parents[2]
    jni = repo / "android" / "app" / "src" / "main" / "jniLibs"
    for abi in ("arm64-v8a", "armeabi-v7a", "x86_64"):
        lib = jni / abi / "libcodec2.so"
        if not lib.is_file():
            pytest.skip(f"missing jniLibs {lib}: not an Android build")
        assert lib.stat().st_size > 100_000


def test_android_lxst_wheel_get_codec_guards_missing_codec2():
    import zipfile

    repo = Path(__file__).resolve().parents[2]
    whl = repo / "android" / "vendor" / "lxst-0.4.8-py3-none-any.whl"
    if not whl.is_file():
        pytest.skip("android/vendor/lxst wheel not present (gitignored)")
    with zipfile.ZipFile(whl) as zin:
        telephony = zin.read("LXST/Primitives/Telephony.py").decode()
        codecs_init = zin.read("LXST/Codecs/__init__.py").decode()
    assert "if Codec2 is not None:" in telephony
    assert "_CODEC2_IMPORT_ERROR" in codecs_init


def test_repack_script_bundles_libcodec2(tmp_path):
    import importlib.util
    import zipfile

    repo_root = Path(__file__).resolve().parents[2]
    script = repo_root / "scripts" / "repack-android-pycodec2-wheels.py"
    spec = importlib.util.spec_from_file_location("repack_pycodec2", script)
    repack_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(repack_mod)
    repack_pycodec2_wheel = repack_mod.repack_pycodec2_wheel

    lib_wheel = (
        tmp_path / "chaquopy_libcodec2-1.2.0-0-py3-none-android_24_arm64_v8a.whl"
    )
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
