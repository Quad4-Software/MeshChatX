"""Microbenchmarks for LXMFy hot paths.

Run standalone with ``pytest tests/benchmarks --benchmark-only``.
In the normal suite these execute once each like regular tests.
"""

from types import SimpleNamespace

import RNS

from lxmfy._sync import run_sync
from lxmfy.debugger import normalize_destination_hex, parse_destination_hash
from lxmfy.lxmf_fields import FIELD_COMMANDS, pack_result, unpack_commands
from lxmfy.permissions import DefaultPerms, PermissionManager
from lxmfy.signatures import SignatureManager
from lxmfy.storage import JSONStorage, Storage


def _message():
    return SimpleNamespace(
        source_hash=b"\x11" * 16,
        destination_hash=b"\x22" * 16,
        content=b"benchmark message content",
        title=b"benchmark title",
        timestamp=1234567890.0,
        fields={FIELD_COMMANDS: [{"command": "ping", "args": []}]},
    )


def test_bench_unpack_commands(benchmark):
    fields = {FIELD_COMMANDS: [{"command": "ping", "args": []} for _ in range(8)]}
    result = benchmark(unpack_commands, fields)
    assert len(result) == 8


def test_bench_pack_result(benchmark):
    result = benchmark(pack_result, {"ok": True}, request_id="req-1")
    assert result


def test_bench_canonicalize_message(benchmark):
    message = _message()
    canonical = benchmark(SignatureManager._canonicalize_message, message)
    assert canonical


def test_bench_sign_message(benchmark):
    identity = RNS.Identity()
    manager = SignatureManager(SimpleNamespace(config=None))
    message = _message()
    signature = benchmark(manager.sign_message, message, identity)
    assert signature


def test_bench_destination_hex_normalize(benchmark):
    result = benchmark(
        normalize_destination_hex,
        "AB:CD:EF:01:23:45:67:89:AB:CD:EF:01:23:45:67:89",
    )
    assert result


def test_bench_destination_hash_parse(benchmark):
    result = benchmark(parse_destination_hash, "a" * 32)
    assert result == b"\xaa" * 16


def test_bench_storage_roundtrip(tmp_path, benchmark):
    storage = Storage(JSONStorage(str(tmp_path / "bench")))

    def roundtrip():
        storage.set("bench:key", {"v": list(range(50))})
        return storage.get("bench:key")

    result = benchmark(roundtrip)
    assert result


def test_bench_permission_check(tmp_path, benchmark):
    perms = PermissionManager(storage=Storage(JSONStorage(str(tmp_path / "p"))))
    perms.enabled = True
    result = benchmark(perms.has_permission, "deadbeef" * 4, DefaultPerms.USE_BOT)
    assert isinstance(result, bool)


def test_bench_run_sync(benchmark):
    def work():
        return sum(range(100))

    result = benchmark(run_sync, work)
    assert result == 4950
