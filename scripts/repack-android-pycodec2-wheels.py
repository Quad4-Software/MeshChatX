#!/usr/bin/env python3
# SPDX-License-Identifier: 0BSD

"""Bundle libcodec2.so into Chaquopy pycodec2 wheels (Android vendor dir)."""

from __future__ import annotations

import argparse
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path


def _abi_tag_from_wheel_name(name: str) -> str | None:
    match = re.search(r"android_\d+_(arm64_v8a|armeabi_v7a|x86_64)", name)
    return match.group(1) if match else None


def _extract_libcodec2(lib_wheel: Path, dest_dir: Path) -> Path | None:
    with zipfile.ZipFile(lib_wheel) as zf:
        for name in zf.namelist():
            if name.endswith("chaquopy/lib/libcodec2.so"):
                zf.extract(name, dest_dir)
                return dest_dir / name
    return None


def _find_libcodec2(vendor_dir: Path, abi_tag: str, dest_dir: Path) -> Path | None:
    matches = sorted(vendor_dir.glob(f"chaquopy_libcodec2-*-android_*_{abi_tag}.whl"))
    if not matches:
        return None
    return _extract_libcodec2(matches[-1], dest_dir)


def repack_pycodec2_wheel(pycodec2_wheel: Path, libcodec2_so: Path) -> bool:
    if not libcodec2_so.is_file():
        print(f"Missing libcodec2.so for {pycodec2_wheel.name}", file=sys.stderr)
        return False

    with tempfile.TemporaryDirectory(prefix="repack-pycodec2-") as tmp_dir:
        root = Path(tmp_dir)
        with zipfile.ZipFile(pycodec2_wheel) as zin:
            zin.extractall(root)

        target = root / "pycodec2" / "libcodec2.so"
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(libcodec2_so, target)

        tmp_wheel = pycodec2_wheel.with_suffix(".repack.whl")
        with zipfile.ZipFile(
            tmp_wheel,
            "w",
            compression=zipfile.ZIP_DEFLATED,
        ) as zout:
            for path in sorted(root.rglob("*")):
                if path.is_file():
                    zout.write(path, path.relative_to(root).as_posix())

        tmp_wheel.replace(pycodec2_wheel)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--vendor-dir",
        type=Path,
        default=Path("android/vendor"),
        help="Directory containing pycodec2 and chaquopy_libcodec2 wheels",
    )
    args = parser.parse_args()
    vendor_dir = args.vendor_dir.resolve()
    if not vendor_dir.is_dir():
        print(f"Vendor directory not found: {vendor_dir}", file=sys.stderr)
        return 1

    wheels = sorted(vendor_dir.glob("pycodec2-*-android_*.whl"))
    if not wheels:
        print(f"No pycodec2 Android wheels under {vendor_dir}", file=sys.stderr)
        return 1

    ok = True
    for wheel in wheels:
        abi_tag = _abi_tag_from_wheel_name(wheel.name)
        if not abi_tag:
            print(f"Skipping unrecognized wheel name: {wheel.name}", file=sys.stderr)
            ok = False
            continue
        with tempfile.TemporaryDirectory(prefix="libcodec2-src-") as lib_tmp:
            libcodec2 = _find_libcodec2(vendor_dir, abi_tag, Path(lib_tmp))
            if libcodec2 is None:
                print(f"No chaquopy_libcodec2 wheel for ABI {abi_tag}", file=sys.stderr)
                ok = False
                continue
            if not repack_pycodec2_wheel(wheel, libcodec2):
                ok = False
                continue
        print(f"Repacked {wheel.name} with pycodec2/libcodec2.so")

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
