"""Unit tests for protocol and transfer helpers."""

import io

import pytest

from rns_filesync import protocol
from rns_filesync.constants import BLOCK_SIZE
from rns_filesync.transfer import (
    apply_delta_blocks,
    build_delta_payload,
    commit_received_file,
    create_empty_file,
    write_bytes_atomic,
)

pytestmark = pytest.mark.unit


def test_protocol_roundtrip():
    raw = protocol.make_file_request("a/b.txt")
    msg = protocol.decode_message(raw)
    assert msg["type"] == protocol.MSG_FILE_REQUEST
    assert msg["path"] == "a/b.txt"


def test_protocol_rejects_unknown():
    bad = protocol.encode_message({"type": "nope"})
    with pytest.raises(protocol.ProtocolError):
        protocol.decode_message(bad)


def test_write_and_empty(tmp_path):
    root = tmp_path / "sync"
    root.mkdir()
    path = write_bytes_atomic(str(root), "nested/x.bin", b"abc")
    assert open(path, "rb").read() == b"abc"
    empty = create_empty_file(str(root), "empty.txt")
    assert os_path_size(empty) == 0


def os_path_size(path: str) -> int:
    import os

    return os.path.getsize(path)


def test_delta_apply(tmp_path):
    import os

    root = tmp_path / "sync"
    root.mkdir()
    original = b"A" * BLOCK_SIZE + b"B" * BLOCK_SIZE + b"C" * 20
    write_bytes_atomic(str(root), "f.bin", original)
    dest = os.path.join(root, "f.bin")
    with open(dest, "r+b") as handle:
        handle.seek(BLOCK_SIZE)
        handle.write(b"\x00" * BLOCK_SIZE)
    peer = tmp_path / "peer.bin"
    peer.write_bytes(original)
    payload = build_delta_payload(str(peer), [1])
    apply_delta_blocks(
        str(root),
        "f.bin",
        [1],
        io.BytesIO(payload),
        expected_size=len(original),
    )
    assert open(dest, "rb").read() == original


def test_commit_full_and_verify(tmp_path):
    root = tmp_path / "sync"
    root.mkdir()
    data = b"payload-data"
    import hashlib
    import tempfile

    digest = hashlib.sha256(data).hexdigest()
    fd, tmp = tempfile.mkstemp(dir=root)
    os_close_write(fd, tmp, data)
    commit_received_file(
        str(root),
        "out.bin",
        mode="full",
        resource_data=open(tmp, "rb"),
        expected_hash=digest,
    )
    assert (root / "out.bin").read_bytes() == data


def os_close_write(fd, path, data):
    import os

    with os.fdopen(fd, "wb") as handle:
        handle.write(data)
