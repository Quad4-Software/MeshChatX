# SPDX-License-Identifier: 0BSD
"""Blockmap generation, verification and rolling-checksum block reuse.

A blockmap describes a target artifact as fixed-size blocks, each with a
weak rolling checksum and a strong sha256. The client scans the currently
installed artifact (or a previous local download) with the same rolling
checksum and copies matching blocks locally, fetching only missing ranges.

Weak checksum (must match scripts/build/update_manifest.py):
    weak = (S*31 + T*65599) mod 2**32
    S = sum(block bytes)
    T = sum((j+1) * block[j])

The scan evaluates the same formula at every byte offset using numpy
cumsums, so identical content hashes identically regardless of position.
"""

from __future__ import annotations

import gzip
import hashlib
import time as _time
from pathlib import Path

import numpy as np

from meshchatx.src.backend.update_types import (
    BLOCKMAP_MAX_BYTES,
    BLOCKMAP_MAX_DECOMPRESSED,
    FULL_DOWNLOAD_MISS_RATIO,
    MAX_BLOCK_SIZE,
    MIN_BLOCK_SIZE,
    UpdateVerifyError,
    sha256_hex,
)

_WEAK_A = 31
_WEAK_B = 65599
_U32 = np.uint64(0xFFFFFFFF)


def _block_checksums(data: bytes) -> tuple[int, str]:
    arr = np.frombuffer(data, dtype=np.uint8).astype(np.uint64)
    n = arr.size
    s = int(arr.sum(dtype=np.uint64)) & 0xFFFFFFFF
    t = (
        int((arr * (np.arange(n, dtype=np.uint64) + 1)).sum(dtype=np.uint64))
        & 0xFFFFFFFF
    )
    weak = (s * _WEAK_A + t * _WEAK_B) & 0xFFFFFFFF
    return weak, hashlib.sha256(data).hexdigest()


def weak_checksum(block: bytes) -> int:
    return _block_checksums(block)[0]


def build_blockmap(path, block_size: int = 512 * 1024) -> dict:
    """Build a blockmap for a file. Returns the unpacked dict."""
    if block_size < MIN_BLOCK_SIZE or block_size > MAX_BLOCK_SIZE:
        raise ValueError("block_size out of range")
    p = Path(path)
    size = p.stat().st_size
    blocks = []
    with open(p, "rb") as fh:
        while True:
            data = fh.read(block_size)
            if not data:
                break
            weak, strong = _block_checksums(data)
            blocks.append([weak, strong])
            if len(data) < block_size:
                break
    return {"v": 1, "block_size": block_size, "size": size, "blocks": blocks}


def encode_blockmap(blockmap: dict) -> bytes:
    """Serialize blockmap as gzip(msgpack). Compact on the wire."""
    from RNS.vendor import umsgpack as mp

    raw = mp.packb(blockmap, use_bin_type=True)
    return gzip.compress(raw, compresslevel=9, mtime=0)


def decode_blockmap(data: bytes, expected_sha256: str | None = None) -> dict:
    if len(data) > BLOCKMAP_MAX_BYTES:
        raise UpdateVerifyError("blockmap exceeds size cap")
    if expected_sha256 and sha256_hex(data) != expected_sha256.lower():
        raise UpdateVerifyError("blockmap sha256 mismatch")
    try:
        raw = gzip.decompress(data)
    except Exception as e:
        raise UpdateVerifyError(f"blockmap decompress failed: {e}") from e
    if len(raw) > BLOCKMAP_MAX_DECOMPRESSED:
        raise UpdateVerifyError("blockmap decompressed size cap exceeded")
    from RNS.vendor import umsgpack as mp

    try:
        obj = mp.unpackb(raw)
    except Exception as e:
        raise UpdateVerifyError(f"blockmap decode failed: {e}") from e
    if not isinstance(obj, dict) or obj.get("v") != 1:
        raise UpdateVerifyError("unrecognized blockmap")
    bs = obj.get("block_size")
    blocks = obj.get("blocks")
    size = obj.get("size")
    if not isinstance(bs, int) or bs < MIN_BLOCK_SIZE or bs > MAX_BLOCK_SIZE:
        raise UpdateVerifyError("blockmap block_size invalid")
    if not isinstance(blocks, list) or not blocks:
        raise UpdateVerifyError("blockmap blocks invalid")
    if not isinstance(size, int) or size < 0:
        raise UpdateVerifyError("blockmap size invalid")
    expected_count = (size + bs - 1) // bs
    if len(blocks) != expected_count:
        raise UpdateVerifyError("blockmap block count mismatch")
    for b in blocks:
        if not isinstance(b, (list, tuple)) or len(b) != 2:
            raise UpdateVerifyError("blockmap block entry invalid")
        weak, strong = b
        if not isinstance(weak, int) or not (0 <= weak <= 0xFFFFFFFF):
            raise UpdateVerifyError("blockmap weak checksum invalid")
        if not isinstance(strong, str) or len(strong) != 64:
            raise UpdateVerifyError("blockmap strong checksum invalid")
    return obj


class BlockMatcher:
    """Scan an existing file for blocks described by a blockmap.

    Returns, for each new-file block index, either (old_offset, length)
    into the old file or None when no match was found. Uses numpy cumsums
    for the rolling weak checksum so a ~200MB scan finishes quickly.
    """

    def __init__(self, blockmap: dict, *, max_seconds: float = 30.0):
        self.block_size = int(blockmap["block_size"])
        self.size = int(blockmap["size"])
        self.blocks = blockmap["blocks"]
        self.max_seconds = max_seconds

    def match(self, old_path) -> list:
        """Return per-block (old_offset, block_len) or None."""
        p = Path(old_path)
        try:
            old_size = p.stat().st_size
        except OSError:
            return [None] * len(self.blocks)
        result: list[tuple[int, int] | None] = [None] * len(self.blocks)
        bs = self.block_size
        if old_size < bs:
            return result
        start = _time.monotonic()

        weak_to_indices = {}
        for idx, (weak, _s) in enumerate(self.blocks):
            weak_to_indices.setdefault(int(weak), []).append(idx)

        expected = np.array([int(w) for w, _s in self.blocks], dtype=np.uint64)
        order = np.argsort(expected)
        sorted_expected = expected[order]

        chunk = 4 * 1024 * 1024
        overlap = bs - 1
        pending = b""
        base_offset = 0
        matched_count = 0

        with open(p, "rb") as fh:
            while True:
                if _time.monotonic() - start > self.max_seconds:
                    raise TimeoutError("block scan exceeded time budget")
                data = fh.read(chunk)
                if not data and not pending:
                    break
                buf = pending + data
                buf_base = base_offset - len(pending)
                n_win = len(buf) - bs + 1
                if n_win <= 0:
                    pending = buf[-overlap:] if len(buf) > overlap else buf
                    base_offset = buf_base + len(buf) - len(pending)
                    if not data:
                        break
                    continue

                arr = np.frombuffer(buf, dtype=np.uint8).astype(np.uint64)
                c1 = np.concatenate(([np.uint64(0)], np.cumsum(arr, dtype=np.uint64)))
                idx_w = (
                    np.arange(arr.size, dtype=np.uint64) + np.uint64(buf_base)
                ) * arr
                c2 = np.concatenate(([np.uint64(0)], np.cumsum(idx_w, dtype=np.uint64)))

                s = (c1[bs : bs + n_win] - c1[:n_win]) & _U32
                u = (c2[bs : bs + n_win] - c2[:n_win]) & _U32
                ii = (np.arange(n_win, dtype=np.uint64) + np.uint64(buf_base)) & _U32
                # T_i = sum_{k=i}^{i+bs-1} (k-i+1)*d[k] = U_i - (i-1)*S_i
                t = (u - ((ii + _U32) & _U32) * s) & _U32
                weak = (s * np.uint64(_WEAK_A) + t * np.uint64(_WEAK_B)) & _U32

                pos = np.searchsorted(sorted_expected, weak)
                pos_clip = np.clip(pos, 0, sorted_expected.size - 1)
                hits = np.nonzero(sorted_expected[pos_clip] == weak)[0]
                for h in hits:
                    win_start = int(h)
                    global_off = buf_base + win_start
                    fh.seek(global_off)
                    block_bytes = fh.read(bs)
                    if len(block_bytes) != bs:
                        continue
                    strong = hashlib.sha256(block_bytes).hexdigest()
                    for bidx in weak_to_indices.get(int(weak[win_start]), []):
                        if result[bidx] is None and self.blocks[bidx][1] == strong:
                            result[bidx] = (global_off, bs)
                            matched_count += 1
                            break
                    if matched_count == len(self.blocks):
                        return result

                keep = overlap
                pending = buf[-keep:] if len(buf) > keep else buf
                base_offset = buf_base + len(buf) - len(pending)
                if not data:
                    break
        return result

    def plan(self, old_path) -> dict:
        """Match blocks; produce copy ranges and missing block indices."""
        matches = self.match(old_path)
        copy_ranges = []
        missing = []
        bs = self.block_size
        for idx, m in enumerate(matches):
            new_off = idx * bs
            if m is not None:
                old_off, length = m
                copy_ranges.append((old_off, new_off, length))
            else:
                missing.append(idx)
        # short tail block is not covered by the rolling scan; try the
        # aligned tail position of the old file directly
        tail_len = self.size - (len(self.blocks) - 1) * bs
        if 0 < tail_len < bs:
            tail_idx = len(self.blocks) - 1
            if matches[tail_idx] is None:
                try:
                    old_size = Path(old_path).stat().st_size
                except OSError:
                    old_size = -1
                try:
                    if old_size >= tail_len:
                        with open(old_path, "rb") as fh:
                            fh.seek(old_size - tail_len)
                            tail = fh.read(tail_len)
                        if hashlib.sha256(tail).hexdigest() == self.blocks[tail_idx][1]:
                            copy_ranges.append(
                                (old_size - tail_len, tail_idx * bs, tail_len)
                            )
                            missing = [i for i in missing if i != tail_idx]
                except OSError:
                    pass
        copy_ranges.sort(key=lambda r: r[1])
        return {
            "matches": matches,
            "copy_ranges": copy_ranges,
            "missing": missing,
            "block_size": bs,
            "matched_bytes": sum(ln for _o, _n, ln in copy_ranges),
            "missing_bytes": sum(min(bs, self.size - i * bs) for i in missing),
        }


def missing_ranges(missing: list, block_size: int, total_size: int) -> list:
    """Coalesce adjacent missing block indices into byte ranges."""
    ranges = []
    for idx in sorted(missing):
        start = idx * block_size
        end = min(start + block_size, total_size)
        if ranges and ranges[-1][1] == start:
            ranges[-1] = (ranges[-1][0], end)
        else:
            ranges.append((start, end))
    return ranges


def blockmap_name(artifact_name: str) -> str:
    return artifact_name + ".blockmap"


def verify_blockmap_entry(entry: dict, blockmap_bytes: bytes) -> dict:
    """Decode and cross-check a fetched blockmap against the manifest entry."""
    bm = decode_blockmap(blockmap_bytes, entry.get("blockmap_sha256"))
    if entry.get("block_size") and bm["block_size"] != entry["block_size"]:
        raise UpdateVerifyError("blockmap block_size does not match manifest")
    if entry.get("block_count") and len(bm["blocks"]) != entry["block_count"]:
        raise UpdateVerifyError("blockmap block_count does not match manifest")
    return bm


def plan_is_viable(plan: dict, total_size: int) -> bool:
    """Decide whether block reuse beats a full download."""
    if plan["missing_bytes"] <= 0:
        return True
    if plan["matched_bytes"] == 0:
        return False
    reuse_ratio = plan["matched_bytes"] / max(1, total_size)
    return reuse_ratio >= (1.0 - FULL_DOWNLOAD_MISS_RATIO) or (
        plan["missing_bytes"] < total_size * 0.5
    )
