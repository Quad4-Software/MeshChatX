"""Local file inventory, hashing, and persistence."""

from __future__ import annotations

import hashlib
import json
import os
import threading
from typing import Any

from rns_filesync.constants import BLOCK_SIZE, HASH_CHUNK_SIZE, HASH_DB_NAME
from rns_filesync.paths import PathJailError, normalize_relpath, relative_to_root


def hash_file(filepath: str) -> str | None:
    """Return SHA-256 hex digest of a file, or None on error."""
    hasher = hashlib.sha256()
    try:
        with open(filepath, "rb") as handle:
            while chunk := handle.read(HASH_CHUNK_SIZE):
                hasher.update(chunk)
        return hasher.hexdigest()
    except OSError:
        return None


def hash_blocks(filepath: str, block_size: int = BLOCK_SIZE) -> list[dict[str, Any]]:
    """Return per-block SHA-256 hashes for delta sync."""
    blocks: list[dict[str, Any]] = []
    try:
        with open(filepath, "rb") as handle:
            block_num = 0
            while block := handle.read(block_size):
                blocks.append(
                    {
                        "num": block_num,
                        "hash": hashlib.sha256(block).hexdigest(),
                        "size": len(block),
                    },
                )
                block_num += 1
    except OSError:
        return []
    return blocks


def differing_block_nums(
    local_blocks: list[dict[str, Any]],
    peer_block_hashes: list[str],
) -> list[int]:
    """Return block numbers present locally that the peer does not have."""
    peer_set = set(peer_block_hashes)
    return [b["num"] for b in local_blocks if b["hash"] not in peer_set]


def decide_sync_action(
    local_info: dict[str, Any] | None,
    peer_info: dict[str, Any] | None,
) -> str:
    """Decide sync action for one path.

    Returns one of: skip, request_full, request_delta, ignore.
    """
    if peer_info is None:
        return "ignore"
    if local_info is None:
        return "request_full"
    if local_info.get("hash") == peer_info.get("hash"):
        return "skip"
    if local_info.get("size", 0) > 0:
        return "request_delta"
    return "request_full"


class Inventory:
    """Tracks file hashes under a sync directory."""

    def __init__(self, sync_directory: str):
        self.sync_directory = os.path.realpath(sync_directory)
        self._lock = threading.RLock()
        self._files: dict[str, dict[str, Any]] = {}

    def load(self) -> int:
        db_path = os.path.join(self.sync_directory, HASH_DB_NAME)
        if not os.path.isfile(db_path):
            with self._lock:
                self._files = {}
            return 0
        try:
            with open(db_path, encoding="utf-8") as handle:
                data = json.load(handle)
            if not isinstance(data, dict):
                data = {}
        except (OSError, json.JSONDecodeError):
            data = {}
        with self._lock:
            self._files = data
        return len(data)

    def save(self) -> None:
        db_path = os.path.join(self.sync_directory, HASH_DB_NAME)
        tmp_path = db_path + ".tmp"
        with self._lock:
            payload = dict(self._files)
        with open(tmp_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
        os.replace(tmp_path, db_path)

    def get(self, relpath: str) -> dict[str, Any] | None:
        with self._lock:
            info = self._files.get(relpath)
            return dict(info) if info else None

    def snapshot(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            return {k: dict(v) for k, v in self._files.items()}

    def set_file(self, relpath: str, info: dict[str, Any]) -> None:
        with self._lock:
            self._files[relpath] = dict(info)

    def remove_file(self, relpath: str) -> None:
        with self._lock:
            self._files.pop(relpath, None)

    def _hash_if_needed(
        self,
        abspath: str,
        relpath: str,
        size: int,
        mtime: float,
    ) -> dict[str, Any] | None:
        with self._lock:
            cached = self._files.get(relpath)
        if (
            cached
            and cached.get("size") == size
            and abs(float(cached.get("mtime", 0)) - mtime) < 1e-6
            and cached.get("hash")
        ):
            return {
                "hash": cached["hash"],
                "size": size,
                "mtime": mtime,
            }
        digest = hash_file(abspath)
        if not digest:
            return None
        return {"hash": digest, "size": size, "mtime": mtime}

    def scan(self) -> dict[str, dict[str, Any]]:
        """Scan sync directory and return current file map."""
        found: dict[str, dict[str, Any]] = {}
        for root, _dirs, files in os.walk(self.sync_directory):
            for filename in files:
                if filename == HASH_DB_NAME or filename.startswith(".rns-filesync"):
                    continue
                abspath = os.path.join(root, filename)
                try:
                    relpath = relative_to_root(self.sync_directory, abspath)
                except PathJailError:
                    continue
                try:
                    stat = os.stat(abspath)
                except OSError:
                    continue
                info = self._hash_if_needed(
                    abspath,
                    relpath,
                    stat.st_size,
                    stat.st_mtime,
                )
                if info:
                    found[relpath] = info
        with self._lock:
            self._files = found
        return self.snapshot()

    def update_from_path(self, relpath: str) -> dict[str, Any] | None:
        try:
            safe = normalize_relpath(relpath)
            abspath = os.path.join(self.sync_directory, safe)
            if not os.path.isfile(abspath):
                self.remove_file(safe)
                return None
            stat = os.stat(abspath)
            info = {
                "hash": hash_file(abspath),
                "size": stat.st_size,
                "mtime": stat.st_mtime,
            }
            if not info["hash"]:
                return None
            self.set_file(safe, info)
            return info
        except (OSError, PathJailError):
            return None
