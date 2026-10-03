# SPDX-License-Identifier: 0BSD

"""Remote Bergamot model catalog for the Translator tool.

Fetches the Firefox Remote Settings translations-models collection, groups
records into language pairs, and downloads verified model files for pack
installation. Downloads are zstd-compressed on the CDN and each record carries
a sha256 of the decompressed payload, so files are verified after decode.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import tempfile

import aiohttp

from meshchatx.src.backend.translation_pack_manager import TranslationPackError

CATALOG_URL = (
    "https://firefox.settings.services.mozilla.com/v1/buckets/"
    "main/collections/translations-models-v2/records"
)
ATTACHMENT_CDN = "https://firefox-settings-attachments.cdn.mozilla.net"

_REQUIRED_FILE_TYPES = ("model", "lex", "vocab")
_ARCH_PREFERENCE = ("base", "base-memory", "tiny")
_MAX_FILE_BYTES = 256 * 1024 * 1024
_MAX_PACK_BYTES = 512 * 1024 * 1024


def _write_file(path: str, data: bytes) -> None:
    with open(path, "wb") as fh:
        fh.write(data)


def _decompress_zstd(payload: bytes) -> bytes:
    try:
        from compression import zstd

        return zstd.decompress(payload)
    except ImportError:
        pass
    try:
        import zstandard  # type: ignore[import-not-found]

        return zstandard.ZstdDecompressor().decompress(
            payload, max_output_size=_MAX_PACK_BYTES
        )
    except ImportError:
        raise TranslationPackError(
            "zstd decompression unavailable on this build, import packs manually"
        ) from None


def group_records_by_pair(records: list[dict]) -> dict[str, dict]:
    """Group catalog records by pair code, preferring base then base-memory."""
    pairs: dict[str, dict] = {}
    by_pair_arch: dict[tuple, list[dict]] = {}
    for rec in records:
        src = str(rec.get("sourceLanguage") or "").lower()
        tgt = str(rec.get("targetLanguage") or "").lower()
        arch = str(rec.get("architecture") or "")
        if len(src) != 2 or len(tgt) != 2 or arch not in _ARCH_PREFERENCE:
            continue
        by_pair_arch.setdefault((src + tgt, arch), []).append(rec)

    grouped: dict[str, dict[str, list[dict]]] = {}
    for (pair, arch), recs in by_pair_arch.items():
        grouped.setdefault(pair, {})[arch] = recs

    for pair, arch_map in grouped.items():
        arch = next((a for a in _ARCH_PREFERENCE if a in arch_map), None)
        if arch is None:
            continue
        recs = arch_map[arch]
        file_types = {str(r.get("fileType") or "") for r in recs}
        if not all(t in file_types for t in _REQUIRED_FILE_TYPES):
            continue
        files = []
        total = 0
        for rec in recs:
            att = rec.get("attachment") or {}
            location = str(att.get("location") or "")
            name = str(rec.get("name") or "")
            if not location or not name:
                continue
            files.append(
                {
                    "name": name,
                    "type": rec.get("fileType"),
                    "location": location,
                    "compressed_size": int(att.get("size") or 0),
                    "decompressed_size": int(rec.get("decompressedSize") or 0),
                    "decompressed_hash": str(rec.get("decompressedHash") or ""),
                }
            )
            total += int(rec.get("decompressedSize") or att.get("size") or 0)
        pairs[pair] = {
            "pair": pair,
            "from": pair[:2],
            "to": pair[2:4],
            "architecture": arch,
            "size": total,
            "files": files,
        }
    return pairs


async def fetch_catalog(timeout: aiohttp.ClientTimeout) -> dict[str, dict]:
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(CATALOG_URL) as resp:
            resp.raise_for_status()
            data = await resp.json(content_type=None)
    records = data.get("data") if isinstance(data, dict) else None
    if not isinstance(records, list):
        raise TranslationPackError("Unexpected catalog response shape")
    return group_records_by_pair(records)


async def download_pair_files(
    pair_entry: dict,
    dest_dir: str,
    timeout: aiohttp.ClientTimeout,
) -> list[str]:
    """Download, decompress, and verify each file for a pair into dest_dir."""
    pair = pair_entry["pair"]
    pair_dir = os.path.join(dest_dir, pair)
    os.makedirs(pair_dir, exist_ok=True)
    written = []
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            for f in pair_entry["files"]:
                if f["type"] not in (
                    *_REQUIRED_FILE_TYPES,
                    "qualityModel",
                    "srcvocab",
                    "trgvocab",
                ):
                    continue
                url = f"{ATTACHMENT_CDN}/{f['location']}"
                async with session.get(url) as resp:
                    resp.raise_for_status()
                    payload = await resp.read()
                if len(payload) > _MAX_FILE_BYTES:
                    raise TranslationPackError(f"Pack file too large: {f['name']}")
                raw = _decompress_zstd(payload)
                expected = f["decompressed_hash"]
                if expected and hashlib.sha256(raw).hexdigest() != expected:
                    raise TranslationPackError(f"Checksum mismatch for {f['name']}")
                safe_name = os.path.basename(f["name"])
                out_path = os.path.join(pair_dir, safe_name)
                await asyncio.to_thread(_write_file, out_path, raw)
                written.append(out_path)
        return written
    except Exception:
        for path in written:
            try:
                os.remove(path)
            except OSError:
                pass
        raise


def staging_dir(incoming_dir: str) -> str:
    os.makedirs(incoming_dir, exist_ok=True)
    return tempfile.mkdtemp(dir=incoming_dir)
