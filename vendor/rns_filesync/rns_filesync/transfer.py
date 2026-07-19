"""File transfer helpers: atomic write and delta apply."""

from __future__ import annotations

import os
import tempfile
from typing import BinaryIO

from rns_filesync.constants import BLOCK_SIZE
from rns_filesync.inventory import hash_file
from rns_filesync.paths import PathJailError, resolve_under_root

# Refuse absurd seeks that could sparse-allocate huge files.
MAX_DELTA_BLOCK_NUM = 1_048_576


def ensure_parent_dir(path: str) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def atomic_replace_file(root: str, relpath: str, source_path: str) -> str:
    """Move source_path into jailed destination via os.replace."""
    dest = resolve_under_root(root, relpath)
    ensure_parent_dir(dest)
    os.replace(source_path, dest)
    return dest


def write_bytes_atomic(root: str, relpath: str, data: bytes) -> str:
    """Write bytes to a temp file under root then replace into place."""
    dest = resolve_under_root(root, relpath)
    ensure_parent_dir(dest)
    fd, tmp_path = tempfile.mkstemp(
        prefix=".rns-xfer-",
        suffix=".tmp",
        dir=os.path.dirname(dest) or root,
    )
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, dest)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise
    return dest


def create_empty_file(root: str, relpath: str) -> str:
    return write_bytes_atomic(root, relpath, b"")


def apply_delta_blocks(
    root: str,
    relpath: str,
    block_nums: list[int],
    data_stream: BinaryIO,
    *,
    expected_size: int | None = None,
    block_size: int = BLOCK_SIZE,
) -> str:
    """Apply ordered delta blocks to a file under root.

    Creates the file if missing. Truncates to expected_size when provided.
    """
    dest = resolve_under_root(root, relpath)
    ensure_parent_dir(dest)
    for block_num in block_nums:
        if not isinstance(block_num, int) or isinstance(block_num, bool):
            raise PathJailError("invalid block number")
        if block_num < 0 or block_num > MAX_DELTA_BLOCK_NUM:
            raise PathJailError("block number out of range")
    if expected_size is not None:
        if (
            not isinstance(expected_size, int)
            or isinstance(expected_size, bool)
            or expected_size < 0
            or expected_size > (MAX_DELTA_BLOCK_NUM + 1) * block_size
        ):
            raise PathJailError("expected size out of range")
    mode = "r+b" if os.path.exists(dest) else "w+b"
    with open(dest, mode) as handle:
        for block_num in block_nums:
            block_data = data_stream.read(block_size)
            if not block_data:
                break
            handle.seek(block_num * block_size)
            handle.write(block_data)
        if expected_size is not None:
            handle.truncate(expected_size)
    return dest


def build_delta_payload(
    filepath: str,
    block_nums: list[int],
    block_size: int = BLOCK_SIZE,
) -> bytes:
    """Concatenate selected blocks from filepath into one payload."""
    chunks: list[bytes] = []
    with open(filepath, "rb") as handle:
        for block_num in block_nums:
            if not isinstance(block_num, int) or isinstance(block_num, bool):
                raise PathJailError("invalid block number")
            if block_num < 0 or block_num > MAX_DELTA_BLOCK_NUM:
                raise PathJailError("block number out of range")
            handle.seek(block_num * block_size)
            chunks.append(handle.read(block_size))
    return b"".join(chunks)


def verify_file_hash(filepath: str, expected_hash: str | None) -> bool:
    if not expected_hash:
        return False
    actual = hash_file(filepath)
    return actual == expected_hash


def commit_received_file(
    root: str,
    relpath: str,
    *,
    mode: str,
    resource_data,
    block_nums: list[int] | None = None,
    expected_hash: str | None = None,
    expected_size: int | None = None,
    require_hash: bool = True,
) -> str:
    """Commit a received Resource payload into the sync root."""
    if require_hash and not expected_hash:
        raise ValueError(f"missing content hash for {relpath}")

    if mode == "delta":
        if block_nums is None:
            raise ValueError("delta mode requires block_nums")
        resource_data.seek(0)
        dest = apply_delta_blocks(
            root,
            relpath,
            block_nums,
            resource_data,
            expected_size=expected_size,
        )
    else:
        source_name = getattr(resource_data, "name", None)
        if source_name and os.path.isfile(source_name):
            dest = atomic_replace_file(root, relpath, source_name)
        else:
            resource_data.seek(0)
            dest = write_bytes_atomic(root, relpath, resource_data.read())

    if require_hash or expected_hash:
        if not verify_file_hash(dest, expected_hash):
            try:
                os.remove(dest)
            except OSError:
                pass
            raise ValueError(f"hash mismatch for {relpath}")
    return dest
