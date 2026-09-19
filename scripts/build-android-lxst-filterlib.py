#!/usr/bin/env python3
# SPDX-License-Identifier: 0BSD

"""Build per-ABI wheels carrying LXST/filterlib.so for the Chaquopy build.

Upstream LXST ships filterlib blobs only as multiarch-suffixed names such as
filterlib.cpython-311-aarch64-linux-gnu.so. Chaquopy's importer does not list
multiarch suffixes (its EXT_SUFFIX is .cpython-311.so and pip wheels carry
plain .so), so find_spec("LXST.filterlib") never resolves on Android and
Filters.py falls back to a runtime ffi.verify() compile that cannot work
on-device.

Because one filterlib.so filename can only hold one ABI, this script emits a
separate wheel per ABI named

    lxst_filterlib_android-<ver>-py3-none-android_<api>_<abi_tag>.whl

containing a single LXST/filterlib.so, mirroring how the vendored
chaquopy_libcodec2 wheels work. pip resolves the matching wheel per ABI.

Examples:
    python3 scripts/build-android-lxst-filterlib.py \
        --out-dir android/vendor --abis arm64-v8a

    python3 scripts/build-android-lxst-filterlib.py \
        --out-dir android/vendor --check --abis arm64-v8a,x86_64

"""

from __future__ import annotations

import argparse
import base64
import hashlib
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

# Gradle ABI name -> (NDK clang triple, wheel abi_tag)
ABI_MAP = {
    "arm64-v8a": ("aarch64-linux-android", "arm64_v8a"),
    "x86_64": ("x86_64-linux-android", "x86_64"),
    "armeabi-v7a": ("armv7a-linux-androideabi", "armeabi_v7a"),
}

DIST = "lxst_filterlib_android"
DEFAULT_VERSION = "0.5.1"
DEFAULT_API = 24


def _detect_ndk() -> Path | None:
    candidates = []
    for env in ("ANDROID_NDK_HOME", "ANDROID_NDK_ROOT", "ANDROID_NDK"):
        val = os.environ.get(env)
        if val:
            candidates.append(Path(val))
    for env in ("ANDROID_HOME", "ANDROID_SDK_ROOT"):
        val = os.environ.get(env)
        if not val:
            continue
        ndk_parent = Path(val) / "ndk"
        if ndk_parent.is_dir():
            versions = sorted(
                (p for p in ndk_parent.iterdir() if p.is_dir()),
                key=lambda p: [int(x) for x in p.name.split(".") if x.isdigit()],
                reverse=True,
            )
            candidates.extend(versions)
    for cand in candidates:
        if (cand / "toolchains" / "llvm" / "prebuilt").is_dir():
            return cand
    return None


def _clang_bin(ndk_dir: Path, triple: str, api: int) -> Path:
    prebuilt = ndk_dir / "toolchains" / "llvm" / "prebuilt"
    for host in sorted(p for p in prebuilt.iterdir() if p.is_dir()):
        clang = host / "bin" / f"{triple}{api}-clang"
        if clang.is_file():
            return clang
    raise SystemExit(
        f"No {triple}{api}-clang under {prebuilt}; check --api or the NDK."
    )


def _wheel_name(version: str, api: int, abi_tag: str) -> str:
    return f"{DIST}-{version}-py3-none-android_{api}_{abi_tag}.whl"


def _record_line(path: str, data: bytes) -> str:
    digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=")
    return f"{path},sha256={digest.decode()},{len(data)}"


def _filters_c_source(args) -> bytes:
    if args.filters_c is not None:
        return args.filters_c.read_bytes()
    # Fall back to the vendored lxst wheel, which ships LXST/Filters.c.
    lxst_wheel = args.lxst_wheel
    if lxst_wheel is None or not lxst_wheel.is_file():
        raise SystemExit(
            "Need --filters-c or a vendored lxst wheel containing LXST/Filters.c"
        )
    with zipfile.ZipFile(lxst_wheel, "r") as zf:
        return zf.read("LXST/Filters.c")


def _build_wheel(
    out_dir: Path, version: str, api: int, abi: str, so_data: bytes
) -> Path:
    _, abi_tag = ABI_MAP[abi]
    dist_info = f"{DIST}-{version}.dist-info"
    wheel_name = _wheel_name(version, api, abi_tag)
    so_name = "LXST/filterlib.so"

    entries: list[tuple[str, bytes]] = [(so_name, so_data)]
    metadata = (
        "Metadata-Version: 2.1\n"
        f"Name: {DIST.replace('_', '-')}\n"
        f"Version: {version}\n"
        "Summary: LXST native filter library for Android (cffi dlopen blob).\n"
    ).encode()
    wheel_meta = (
        "Wheel-Version: 1.0\n"
        "Generator: build-android-lxst-filterlib\n"
        "Root-Is-Purelib: true\n"
        f"Tag: py3-none-android_{api}_{abi_tag}\n"
    ).encode()
    entries.append((f"{dist_info}/METADATA", metadata))
    entries.append((f"{dist_info}/WHEEL", wheel_meta))

    record_lines = [_record_line(name, data) for name, data in entries]
    record_lines.append(f"{dist_info}/RECORD,,")
    entries.append((f"{dist_info}/RECORD", ("\n".join(record_lines) + "\n").encode()))

    out_path = out_dir / wheel_name
    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as zout:
        for name, data in entries:
            zout.writestr(name, data)
    return out_path


def _check(out_dir: Path, version: str, api: int, abis: list[str]) -> int:
    missing = []
    for abi in abis:
        _, abi_tag = ABI_MAP[abi]
        wheel = out_dir / _wheel_name(version, api, abi_tag)
        ok = wheel.is_file()
        if ok:
            try:
                with zipfile.ZipFile(wheel, "r") as zf:
                    ok = "LXST/filterlib.so" in zf.namelist()
            except zipfile.BadZipFile:
                ok = False
        if not ok:
            missing.append(wheel.name)
    if missing:
        print(
            f"Missing filterlib wheels: {', '.join(missing)}. "
            "Run: python3 scripts/build-android-lxst-filterlib.py "
            f"--out-dir {out_dir} --abis {','.join(abis)}",
            file=sys.stderr,
        )
        return 1
    print(f"filterlib wheels present for {', '.join(abis)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=Path("android/vendor"))
    parser.add_argument("--abis", default="arm64-v8a")
    parser.add_argument("--api", type=int, default=DEFAULT_API)
    parser.add_argument("--version", default=DEFAULT_VERSION)
    parser.add_argument("--ndk-dir", type=Path, default=None)
    parser.add_argument("--filters-c", type=Path, default=None)
    parser.add_argument("--lxst-wheel", type=Path, default=None)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    abis = [a.strip() for a in args.abis.split(",") if a.strip()]
    unknown = [a for a in abis if a not in ABI_MAP]
    if unknown:
        raise SystemExit(f"Unsupported ABIs: {', '.join(unknown)}")

    if args.check:
        return _check(args.out_dir, args.version, args.api, abis)

    ndk_dir = args.ndk_dir or _detect_ndk()
    if ndk_dir is None:
        raise SystemExit(
            "No Android NDK found. Set --ndk-dir or ANDROID_HOME/ANDROID_NDK_HOME."
        )
    filters_c = _filters_c_source(args)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as td:
        src = Path(td) / "Filters.c"
        src.write_bytes(filters_c)
        for abi in abis:
            triple, _ = ABI_MAP[abi]
            clang = _clang_bin(ndk_dir, triple, args.api)
            out = Path(td) / "filterlib.so"
            cmd = [
                str(clang),
                "-O2",
                "-fPIC",
                "-shared",
                "-o",
                str(out),
                str(src),
                "-lm",
            ]
            subprocess.run(cmd, check=True)
            wheel = _build_wheel(
                args.out_dir,
                args.version,
                args.api,
                abi,
                out.read_bytes(),
            )
            print(f"built {wheel.name} via {clang.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
