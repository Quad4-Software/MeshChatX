#!/usr/bin/env python3
# SPDX-License-Identifier: 0BSD
"""Build and sign the MeshChatX update manifest (update.json / update.rsm).

The manifest is a canonical JSON document describing one release: version,
tag, track, release timestamp, an optional minimum_version floor, and every
applicable artifact with sha256, size, platform, arch and kind. The signed
form wraps the canonical JSON in an rnid-compatible RSG envelope (see
meshchatx/src/update_rsm.py), verifiable offline with RNS.Identity against
a pinned signer hash.

Usage:

    # Build an unsigned manifest for inspection:
    python3 scripts/build/update_manifest.py build --assets upload/ \
        --version 4.9.5 --tag v4.9.5 --track release -o upload/update.json

    # Sign it (needs a private .rid identity, see scripts/ci/sign-tree-rsm.sh):
    RNS_ID_PATH=/path/to/release.rid \
    python3 scripts/build/update_manifest.py sign --assets upload/ \
        --version 4.9.5 --tag v4.9.5 --track release \
        -o upload/update.json --rsm upload/update.rsm

    # Verify an rsm against a signer hash (default: the tree-rsm signer):
    python3 scripts/build/update_manifest.py verify upload/update.rsm \
        --signer e46112d44649266d71fe2193e00a4710

Environment:
    RNS_ID_PATH          private identity file for "sign"
    MESHCHATX_UPDATE_MIN_VERSION  default minimum_version (default: 0.0.0)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from meshchatx.src.update_rsm import (
    APP_ID,
    SCHEMA,
    verify_rsm,
)
from meshchatx.src.update_rsm import (
    sign_manifest as _sign_with_identity,
)

TRACKS = ("release", "beta", "testing")
DEFAULT_SIGNER = "e46112d44649266d71fe2193e00a4710"

# Artifact kinds that never describe an installable update payload.
_SKIP_SUFFIXES = (
    ".sha256",
    ".sha512",
    ".sig",
    ".bundle",
    ".json",
    ".rsm",
    ".txt",
    ".md",
    ".flatpakref",
    ".flatpakrepo",
)

_KIND_BY_SUFFIX = {
    ".appimage": "appimage",
    ".deb": "deb",
    ".rpm": "rpm",
    ".apk": "apk",
    ".dmg": "dmg",
    ".exe": "exe",
    ".msi": "msi",
    ".zip": "zip",
    ".whl": "wheel",
    ".pyz": "pyz",
    ".flatpak": "flatpak",
}

_KIND_PLATFORM = {
    "appimage": "linux",
    "deb": "linux",
    "rpm": "linux",
    "flatpak": "linux",
    "apk": "android",
    "dmg": "macos",
    "exe": "windows",
    "msi": "windows",
    "zip": None,  # decided by name tokens
    "wheel": "python",
    "pyz": "python",
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def classify_artifact(name: str) -> dict | None:
    """Return {kind, platform, arch} for an artifact filename, or None to skip."""
    lower = name.lower()
    if lower.endswith(_SKIP_SUFFIXES):
        return None
    if lower.startswith(("update.", "latest.", "checksums", "sbom", "openvex")):
        return None

    kind = None
    for suffix, k in _KIND_BY_SUFFIX.items():
        if lower.endswith(suffix):
            kind = k
            break
    if kind is None:
        for suffix in (".tar.gz", ".tgz", ".tar.xz"):
            if lower.endswith(suffix):
                kind = "archive"
                break
    if kind is None:
        return None

    plat = _KIND_PLATFORM.get(kind)
    if plat is None or kind == "archive":
        if "linux" in lower:
            plat = "linux"
        elif "mac" in lower or "darwin" in lower:
            plat = "macos"
        elif "win" in lower:
            plat = "windows"
        elif "android" in lower:
            plat = "android"

    if "aarch64" in lower or "arm64" in lower:
        arch = "aarch64"
    elif "armv7" in lower or "armhf" in lower:
        arch = "armv7"
    elif "x86_64" in lower or "x64" in lower or "amd64" in lower:
        arch = "x86_64"
    elif "i386" in lower or "x86" in lower or "win32" in lower:
        arch = "x86"
    else:
        arch = "any"

    return {"kind": kind, "platform": plat, "arch": arch}


def collect_artifacts(assets_dir: Path) -> list[dict]:
    artifacts = []
    for path in sorted(assets_dir.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(assets_dir).as_posix()
        info = classify_artifact(path.name)
        if info is None:
            continue
        artifacts.append(
            {
                "file": rel,
                "sha256": sha256_file(path),
                "size": path.stat().st_size,
                "kind": info["kind"],
                "platform": info["platform"],
                "arch": info["arch"],
            }
        )
    return artifacts


def build_manifest(
    assets_dir: Path,
    *,
    version: str,
    tag: str,
    track: str,
    minimum_version: str | None = None,
    released_at: str | None = None,
) -> dict:
    if track not in TRACKS:
        raise SystemExit(f"unknown track {track!r} (expected one of {TRACKS})")
    return {
        "schema": SCHEMA,
        "app": APP_ID,
        "version": version,
        "tag": tag,
        "track": track,
        "released_at": released_at or datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "minimum_version": minimum_version
        or os.environ.get("MESHCHATX_UPDATE_MIN_VERSION", "0.0.0"),
        "artifacts": collect_artifacts(assets_dir),
    }


def sign_manifest(manifest: dict, identity_path: Path) -> bytes:
    import RNS

    identity = RNS.Identity.from_file(str(identity_path))
    if identity is None:
        raise SystemExit(f"could not load identity from {identity_path}")
    try:
        return _sign_with_identity(manifest, identity)
    except ValueError as e:
        raise SystemExit(str(e)) from e


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)

    def add_common(p):
        p.add_argument("--assets", type=Path, required=True, help="release assets tree")
        p.add_argument("--version", required=True)
        p.add_argument("--tag", required=True)
        p.add_argument("--track", required=True, choices=TRACKS)
        p.add_argument("--minimum-version", default=None)
        p.add_argument("--released-at", default=None)
        p.add_argument("-o", "--out", type=Path, default=None, help="update.json path")

    add_common(sub.add_parser("build"))
    sign_p = sub.add_parser("sign")
    add_common(sign_p)
    sign_p.add_argument(
        "--identity", type=Path, default=None, help=".rid file (or RNS_ID_PATH)"
    )
    sign_p.add_argument(
        "--rsm", type=Path, default=None, help="signed update.rsm output"
    )

    ver_p = sub.add_parser("verify")
    ver_p.add_argument("rsm", type=Path)
    ver_p.add_argument(
        "--signer", default=DEFAULT_SIGNER, help="required signer identity hash (hex)"
    )

    args = parser.parse_args(argv)

    if args.cmd == "verify":
        signer = bytes.fromhex(args.signer)
        try:
            manifest = verify_rsm(args.rsm.read_bytes(), required_signer_hash=signer)
        except ValueError as e:
            print(f"verify: FAILED: {e}", file=sys.stderr)
            return 1
        print(
            f"verify: OK signer={signer.hex()} version={manifest['version']} "
            f"track={manifest['track']} artifacts={len(manifest['artifacts'])}"
        )
        return 0

    manifest = build_manifest(
        args.assets,
        version=args.version,
        tag=args.tag,
        track=args.track,
        minimum_version=args.minimum_version,
        released_at=args.released_at,
    )
    if not manifest["artifacts"]:
        print("update_manifest: no installable artifacts found", file=sys.stderr)
        return 1

    if args.cmd == "sign":
        identity_path = args.identity or os.environ.get("RNS_ID_PATH")
        if not identity_path:
            print("sign: --identity or RNS_ID_PATH required", file=sys.stderr)
            return 1
        rsm = sign_manifest(manifest, Path(identity_path))
        rsm_path = args.rsm or args.assets / "update.rsm"
        rsm_path.write_bytes(rsm)
        print(f"wrote {rsm_path} ({len(rsm)} bytes)")

    out = args.out or args.assets / "update.json"
    out.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"wrote {out} ({len(manifest['artifacts'])} artifacts)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
