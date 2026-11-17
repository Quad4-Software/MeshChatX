#!/usr/bin/env python3
# SPDX-License-Identifier: 0BSD
"""Build, sign and verify the MeshChatX update manifest (schema 2).

Produces, for one channel and version:

    <out>/update-manifest-<channel>.rsm   signed manifest (msgpack payload
                                        in an rnid-compatible RSG envelope)
    <out>/update.json                     human-readable debug view
    <out>/<artifact>.blockmap             gzip(msgpack) block map per
                                        artifact, sha256 recorded inside
                                        the signed manifest

Artifact files themselves are uploaded by the release pipeline to
updates/<channel>/<version>/<name> on static mirrors, or attached to the
GitHub/Forgejo release under their plain names.

Usage:

    python3 scripts/build/update_manifest.py build \
        --assets dist/ --version 4.13.0 --channel stable \
        --identity /path/to/release.rid --out release-assets/

    python3 scripts/build/update_manifest.py verify update-manifest-stable.rsm \
        --signer e46112d44649266d71fe2193e00a4710

Environment:
    RNS_ID_PATH / MESHCHATX_UPDATE_SIGNING_IDENTITY
        private identity file for signing (never committed)
    MESHCHATX_UPDATE_MIN_VERSION   default min_supported_version
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from meshchatx.src import update_rsm
from meshchatx.src.backend.update_blockmap import (
    build_blockmap,
    encode_blockmap,
)
from meshchatx.src.backend.update_types import (
    BLOCK_SIZE,
    CHANNELS,
    MANIFEST_MAX_BYTES,
    mirror_asset_name,
    safe_artifact_name,
)

DEFAULT_SIGNER = "e46112d44649266d71fe2193e00a4710"
DEFAULT_VALID_DAYS = 30

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
    ".blockmap",
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
    "zip": None,
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
    if kind == "archive":
        kind = "tarball"
    return {"kind": kind, "platform": plat, "arch": arch}


def collect_artifacts(assets_dir: Path, block_size: int) -> tuple[list, dict]:
    """Return (manifest artifact entries, {name: blockmap_bytes})."""
    entries = []
    blockmaps = {}
    for path in sorted(assets_dir.rglob("*")):
        if not path.is_file():
            continue
        name = path.name
        if name.endswith(".blockmap") or name in (
            "update.json",
            "checksums.txt",
        ):
            continue
        cls = classify_artifact(name)
        if cls is None:
            continue
        safe = safe_artifact_name(name)
        if safe is None:
            print(f"skip unsafe artifact name: {name}", file=sys.stderr)
            continue
        size = path.stat().st_size
        if size <= 0:
            continue
        bm = build_blockmap(path, block_size)
        bm_bytes = encode_blockmap(bm)
        blockmaps[name] = bm_bytes
        entries.append(
            {
                "name": safe,
                "size": size,
                "sha256": sha256_file(path),
                "kind": cls["kind"],
                "platform": cls["platform"],
                "arch": cls["arch"],
                "blockmap_sha256": hashlib.sha256(bm_bytes).hexdigest(),
                "block_size": bm["block_size"],
                "block_count": len(bm["blocks"]),
            }
        )
    return entries, blockmaps


def build_manifest(args) -> dict:
    assets = Path(args.assets)
    if not assets.is_dir():
        raise SystemExit(f"assets dir not found: {assets}")
    entries, _blockmaps = collect_artifacts(assets, args.block_size)
    now = int(time.time())
    issued = args.issued_at if args.issued_at is not None else now
    valid_until = issued + args.valid_days * 86400
    min_sup = args.min_supported or os.environ.get(
        "MESHCHATX_UPDATE_MIN_VERSION", "0.0.0"
    )
    return {
        "schema": update_rsm.SCHEMA,
        "app": update_rsm.APP_ID,
        "channel": args.channel,
        "version": args.version,
        "tag": args.tag or args.version,
        "issued_at": int(issued),
        "valid_until": int(valid_until),
        "min_supported_version": min_sup,
        "artifacts": entries,
    }


def write_outputs(
    manifest: dict,
    assets_dir: Path,
    out_dir: Path,
    block_size: int,
    do_sign: bool,
    identity_path: Path | None,
):
    out_dir.mkdir(parents=True, exist_ok=True)
    channel = manifest["channel"]
    # blockmaps next to the manifest for the release pipeline to upload
    _entries, blockmaps = collect_artifacts(assets_dir, block_size)
    for name, bm_bytes in blockmaps.items():
        (out_dir / f"{name}.blockmap").write_bytes(bm_bytes)
    rsm_name = mirror_asset_name(channel)
    if do_sign:
        if identity_path is None:
            raise SystemExit("signing requires --identity or RNS_ID_PATH")
        import RNS

        identity = RNS.Identity.from_file(str(identity_path))
        if identity is None:
            raise SystemExit(f"could not load identity from {identity_path}")
        rsm = update_rsm.sign_manifest(manifest, identity)
        if len(rsm) > MANIFEST_MAX_BYTES:
            raise SystemExit("signed manifest exceeds client size cap")
        (out_dir / rsm_name).write_bytes(rsm)
        print(f"wrote {out_dir / rsm_name} ({len(rsm)} bytes)")
    else:
        # unsigned debug form: msgpack payload only, for inspection
        (out_dir / "update-manifest.msgpack").write_bytes(
            update_rsm.manifest_bytes(manifest)
        )
        print(f"wrote unsigned manifest payload to {out_dir}")
    (out_dir / "update.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        f"manifest: channel={channel} version={manifest['version']} "
        f"artifacts={len(manifest['artifacts'])} "
        f"valid_until={manifest['valid_until']}"
    )


def cmd_build(args) -> int:
    manifest = build_manifest(args)
    if not manifest["artifacts"]:
        print(
            "no artifacts classified; refusing to write an empty manifest",
            file=sys.stderr,
        )
        return 1
    identity = (
        args.identity
        or os.environ.get("RNS_ID_PATH")
        or os.environ.get("MESHCHATX_UPDATE_SIGNING_IDENTITY")
    )
    write_outputs(
        manifest,
        Path(args.assets),
        Path(args.out),
        args.block_size,
        do_sign=bool(identity),
        identity_path=Path(identity) if identity else None,
    )
    return 0


def cmd_verify(args) -> int:
    rsm = Path(args.rsm).read_bytes()
    if len(rsm) > MANIFEST_MAX_BYTES:
        print("rsm exceeds size cap", file=sys.stderr)
        return 1
    try:
        manifest = update_rsm.verify_rsm(
            rsm, required_signer_hashes=bytes.fromhex(args.signer)
        )
    except Exception as e:
        print(f"verify failed: {e}", file=sys.stderr)
        return 1
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="build manifest (+blockmaps, optional sign)")
    b.add_argument(
        "--assets",
        type=Path,
        required=True,
        help="directory containing release artifact files",
    )
    b.add_argument("--version", required=True)
    b.add_argument("--channel", required=True, choices=CHANNELS)
    b.add_argument("--tag", default=None)
    b.add_argument("--min-supported", default=None)
    b.add_argument("--issued-at", type=int, default=None)
    b.add_argument("--valid-days", type=int, default=DEFAULT_VALID_DAYS)
    b.add_argument("--block-size", type=int, default=BLOCK_SIZE)
    b.add_argument(
        "--identity",
        type=Path,
        default=None,
        help=".rid signing identity (or RNS_ID_PATH / "
        "MESHCHATX_UPDATE_SIGNING_IDENTITY)",
    )
    b.add_argument(
        "--out",
        type=Path,
        required=True,
        help="output directory for manifest, blockmaps, update.json",
    )
    b.set_defaults(func=cmd_build)

    v = sub.add_parser("verify", help="verify a signed manifest offline")
    v.add_argument("rsm", type=Path)
    v.add_argument(
        "--signer",
        default=DEFAULT_SIGNER,
        help="required signer identity hash (32 or 64 hex)",
    )
    v.set_defaults(func=cmd_verify)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
