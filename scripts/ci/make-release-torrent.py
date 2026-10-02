#!/usr/bin/env python3
# SPDX-License-Identifier: 0BSD
"""Build a BitTorrent v1 torrent with HTTP webseeds (BEP 19).

The torrent name is the release tag so directory webseeds map to
https://cdn.quad4.io/<track>/<tag>/<file> and GitHub
.../releases/download/<tag>/<file>.

Usage:
    python3 scripts/ci/make-release-torrent.py --dir upload --tag v4.9.3 --track release
    python3 scripts/ci/make-release-torrent.py --from-release v4.9.3 --track release --cdn-only
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

PIECE_LENGTH = 2 * 1024 * 1024
USER_AGENT = "meshchatx-torrent/1.0"
GITHUB_API = "https://api.github.com/repos/Quad4-Software/MeshChatX/releases/tags/"
GITHUB_WS = "https://github.com/Quad4-Software/MeshChatX/releases/download/"
CDN_BASE = "https://cdn.quad4.io"
TRACKERS = (
    "udp://tracker.opentrackr.org:1337/announce",
    "udp://open.stealth.si:80/announce",
    "udp://tracker.torrent.eu.org:451/announce",
)
SKIP_SUFFIXES = (
    ".cosign.bundle",
    ".blockmap",
    ".yml",
    ".intoto.jsonl",
)
SKIP_NAMES = frozenset(
    {
        "openvex.json",
        "sbom.cyclonedx.json",
        "builder-debug.yml",
        "library.zip",
        "latest.yml",
    }
)
KEEP_SUFFIXES = (
    ".appimage",
    ".deb",
    ".rpm",
    ".apk",
    ".pyz",
    ".whl",
    ".dmg",
    ".exe",
    ".flatpak",
)


def bencode(value: object) -> bytes:
    if isinstance(value, int) and not isinstance(value, bool):
        return f"i{value}e".encode()
    if isinstance(value, bytes):
        return f"{len(value)}:".encode() + value
    if isinstance(value, str):
        raw = value.encode()
        return f"{len(raw)}:".encode() + raw
    if isinstance(value, list):
        return b"l" + b"".join(bencode(v) for v in value) + b"e"
    if isinstance(value, dict):
        items = sorted(
            ((k.encode() if isinstance(k, str) else k), v) for k, v in value.items()
        )
        out = [b"d"]
        for k, v in items:
            out.append(bencode(k))
            out.append(bencode(v))
        out.append(b"e")
        return b"".join(out)
    raise TypeError(f"cannot bencode {type(value).__name__}")


def include_name(name: str) -> bool:
    base = Path(name).name
    lower = base.lower()
    if base in SKIP_NAMES or lower in SKIP_NAMES:
        return False
    if any(lower.endswith(s) for s in SKIP_SUFFIXES):
        return False
    if lower.endswith(".torrent"):
        return False
    return any(lower.endswith(s) for s in KEEP_SUFFIXES)


def cdn_url(track: str, tag: str, name: str) -> str:
    return f"{CDN_BASE}/{track}/{urllib.parse.quote(tag)}/{urllib.parse.quote(name)}"


def github_url(tag: str, name: str) -> str:
    return f"{GITHUB_WS}{urllib.parse.quote(tag)}/{urllib.parse.quote(name)}"


def head_ok(url: str, timeout: int = 20) -> bool:
    req = urllib.request.Request(
        url, method="HEAD", headers={"User-Agent": USER_AGENT}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 300
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def local_files(directory: Path) -> list[tuple[str, int, Path]]:
    found: list[tuple[str, int, Path]] = []
    for path in sorted(directory.iterdir(), key=lambda p: p.name.lower()):
        if not path.is_file() or not include_name(path.name):
            continue
        found.append((path.name, path.stat().st_size, path))
    return found


def github_assets(tag: str) -> list[tuple[str, int, str]]:
    req = urllib.request.Request(
        f"{GITHUB_API}{urllib.parse.quote(tag)}",
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": USER_AGENT,
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode())
    out: list[tuple[str, int, str]] = []
    for asset in data.get("assets") or []:
        name = str(asset.get("name") or "")
        if not include_name(name):
            continue
        size = int(asset.get("size") or 0)
        url = str(asset.get("browser_download_url") or github_url(tag, name))
        out.append((name, size, url))
    out.sort(key=lambda row: row[0].lower())
    return out


class PieceHasher:
    def __init__(self, piece_length: int) -> None:
        self.piece_length = piece_length
        self._buf = bytearray()
        self.pieces: list[bytes] = []
        self.total = 0

    def feed(self, chunk: bytes) -> None:
        self.total += len(chunk)
        self._buf.extend(chunk)
        while len(self._buf) >= self.piece_length:
            piece = bytes(self._buf[: self.piece_length])
            del self._buf[: self.piece_length]
            self.pieces.append(hashlib.sha1(piece).digest())

    def finish(self) -> bytes:
        if self._buf:
            self.pieces.append(hashlib.sha1(bytes(self._buf)).digest())
            self._buf.clear()
        return b"".join(self.pieces)


def hash_path(path: Path, hasher: PieceHasher) -> None:
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk:
                break
            hasher.feed(chunk)


def hash_url(url: str, hasher: PieceHasher, expected: int) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=120) as resp:
        got = 0
        while True:
            chunk = resp.read(1024 * 1024)
            if not chunk:
                break
            got += len(chunk)
            hasher.feed(chunk)
    if expected and got != expected:
        raise RuntimeError(f"size mismatch for {url}: got {got} expected {expected}")


def magnet_link(infohash: str, name: str, webseeds: list[str], trackers: tuple[str, ...]) -> str:
    parts = [f"magnet:?xt=urn:btih:{infohash}", f"dn={urllib.parse.quote(name)}"]
    for tr in trackers:
        parts.append(f"tr={urllib.parse.quote(tr, safe='')}")
    for ws in webseeds:
        parts.append(f"ws={urllib.parse.quote(ws, safe='')}")
    return "&".join(parts)


def build_torrent(
    *,
    tag: str,
    track: str,
    files: list[tuple[str, int]],
    pieces: bytes,
    piece_length: int = PIECE_LENGTH,
) -> tuple[bytes, str, str]:
    info = {
        "name": tag,
        "piece length": piece_length,
        "pieces": pieces,
        "files": [{"length": size, "path": [name]} for name, size in files],
    }
    payload = {
        "announce": TRACKERS[0],
        "announce-list": [[t] for t in TRACKERS],
        "comment": f"MeshChatX {tag} webseeded from {CDN_BASE}/{track}/",
        "created by": "MeshChatX",
        "creation date": int(time.time()),
        "encoding": "UTF-8",
        "info": info,
        "url-list": [
            f"{CDN_BASE}/{track}/",
            GITHUB_WS,
        ],
    }
    raw = bencode(payload)
    infohash = hashlib.sha1(bencode(info)).hexdigest()
    magnet = magnet_link(infohash, f"MeshChatX-{tag}", payload["url-list"], TRACKERS)
    return raw, infohash, magnet


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--dir", type=Path, help="local directory of release assets")
    src.add_argument("--from-release", metavar="TAG", help="hash assets from GitHub and CDN")
    p.add_argument("--tag", help="release tag, default from --from-release")
    p.add_argument("--track", choices=("release", "beta", "testing"), default="release")
    p.add_argument("--cdn-only", action="store_true", help="keep files that exist on the CDN")
    p.add_argument("--out", type=Path, help="torrent output path")
    p.add_argument("--meta", type=Path, help="optional json sidecar with magnet and infohash")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    tag = args.tag or args.from_release
    if not tag:
        print("tag is required", file=sys.stderr)
        return 2
    track = args.track
    hasher = PieceHasher(PIECE_LENGTH)
    listed: list[tuple[str, int]] = []

    if args.dir is not None:
        rows = local_files(args.dir)
        if args.cdn_only:
            rows = [r for r in rows if head_ok(cdn_url(track, tag, r[0]))]
        if not rows:
            print("no installer files found", file=sys.stderr)
            return 1
        for name, size, path in rows:
            print(f"hash {name} ({size} bytes)", file=sys.stderr)
            hash_path(path, hasher)
            listed.append((name, size))
    else:
        rows_gh = github_assets(tag)
        selected: list[tuple[str, int, str]] = []
        for name, size, gh_url in rows_gh:
            mirror = cdn_url(track, tag, name)
            on_cdn = head_ok(mirror)
            if args.cdn_only and not on_cdn:
                print(f"skip {name} (not on CDN)", file=sys.stderr)
                continue
            selected.append((name, size, mirror if on_cdn else gh_url))
        if not selected:
            print("no installer files found", file=sys.stderr)
            return 1
        for name, size, url in selected:
            print(f"hash {name} from {url}", file=sys.stderr)
            hash_url(url, hasher, size)
            listed.append((name, size))

    pieces = hasher.finish()
    expected = sum(size for _n, size in listed)
    if hasher.total != expected:
        print(
            f"hashed {hasher.total} bytes, expected {expected}",
            file=sys.stderr,
        )
        return 1
    raw, infohash, magnet = build_torrent(
        tag=tag, track=track, files=listed, pieces=pieces
    )
    out = args.out or Path(f"MeshChatX-{tag}.torrent")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(raw)
    meta = {
        "tag": tag,
        "track": track,
        "infohash": infohash,
        "magnet": magnet,
        "pieceLength": PIECE_LENGTH,
        "files": [{"name": n, "size": s} for n, s in listed],
        "webseeds": [f"{CDN_BASE}/{track}/", GITHUB_WS],
        "torrent": out.name,
    }
    meta_path = args.meta or out.with_suffix(".json")
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out} infohash={infohash}", file=sys.stderr)
    print(magnet)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
