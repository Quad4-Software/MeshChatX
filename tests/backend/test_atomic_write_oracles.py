# SPDX-License-Identifier: 0BSD

"""Oracle tests for atomic_write_bytes / atomic_write_text.

Core invariants: a reader or post-crash observer must never see a torn
file (only a complete old or complete new payload), failed writes must
not leave tmp siblings behind, and the requested mode must be pinned on
the final file even when overwriting.
"""

from __future__ import annotations

import os
import threading
import time
import uuid

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from meshchatx.src.path_utils import atomic_write_bytes, atomic_write_text


def _fresh_dir(tmp_path):
    root = tmp_path / str(uuid.uuid4())
    root.mkdir()
    return root


def _siblings(root, keep_name):
    return sorted(p.name for p in root.iterdir() if p.name != keep_name)


class TestConcurrentWriters:
    def test_eight_writers_leave_one_complete_payload(self, tmp_path):
        root = _fresh_dir(tmp_path)
        target = root / "state.bin"
        # Distinct lengths and markers make a torn write easy to spot.
        payloads = [f"writer-{i}|".encode() * (i + 2) + bytes([i]) for i in range(8)]
        barrier = threading.Barrier(len(payloads))
        errors: list[BaseException] = []

        def writer(data):
            barrier.wait()
            try:
                atomic_write_bytes(target, data)
            except BaseException as exc:
                errors.append(exc)

        threads = [
            threading.Thread(target=writer, args=(payload,)) for payload in payloads
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=30)

        assert errors == []
        final = target.read_bytes()
        # The last os.replace wins; the result must be one whole payload.
        assert final in payloads
        # mkstemp siblings are either renamed into place or unlinked.
        assert _siblings(root, target.name) == []

    def test_repeated_concurrent_writes(self, tmp_path):
        root = _fresh_dir(tmp_path)
        target = root / "state.bin"
        payloads = [b"A" * 64 + bytes([i]) for i in range(4)]
        errors: list[BaseException] = []

        def writer(data):
            try:
                for _ in range(10):
                    atomic_write_bytes(target, data)
            except BaseException as exc:
                errors.append(exc)

        threads = [
            threading.Thread(target=writer, args=(payload,)) for payload in payloads
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=60)

        assert errors == []
        assert target.read_bytes() in payloads
        assert _siblings(root, target.name) == []


class TestReaderDuringReplace:
    def test_reader_never_sees_torn_content(self, tmp_path):
        root = _fresh_dir(tmp_path)
        target = root / "live.bin"
        versions = [
            b"v0-" + b"a" * 128,
            b"v1-" + b"bb" * 256,
            b"v2-" + b"ccc" * 64,
        ]
        target.write_bytes(versions[0])
        allowed = set(versions)
        stop = threading.Event()
        seen: list[bytes] = []
        reader_errors: list[BaseException] = []

        def reader():
            while not stop.is_set():
                try:
                    seen.append(target.read_bytes())
                except FileNotFoundError:
                    # os.replace never opens a gap; tolerate defensively.
                    continue
                except BaseException as exc:
                    reader_errors.append(exc)
                    return

        def writer():
            for i in range(60):
                atomic_write_bytes(target, versions[i % len(versions)])
                time.sleep(0.0005)

        reader_thread = threading.Thread(target=reader)
        writer_thread = threading.Thread(target=writer)
        reader_thread.start()
        writer_thread.start()
        writer_thread.join(timeout=60)
        stop.set()
        reader_thread.join(timeout=30)

        assert reader_errors == []
        assert seen, "reader thread never completed a read"
        for data in seen:
            assert data in allowed
        assert _siblings(root, target.name) == []


class TestFailureCleanup:
    def test_replace_failure_keeps_original_and_cleans_tmp(self, tmp_path, monkeypatch):
        root = _fresh_dir(tmp_path)
        target = root / "state.bin"
        target.write_bytes(b"original")

        def boom(_src, _dst):
            raise OSError("simulated replace failure")

        monkeypatch.setattr(os, "replace", boom)
        with pytest.raises(OSError, match="replace failure"):
            atomic_write_bytes(target, b"new-payload")

        assert target.read_bytes() == b"original"
        assert _siblings(root, target.name) == []

    def test_write_failure_cleans_tmp_and_keeps_original(self, tmp_path, monkeypatch):
        root = _fresh_dir(tmp_path)
        target = root / "state.bin"
        target.write_bytes(b"original")
        real_fdopen = os.fdopen

        class _WriteBomb:
            """Proxy whose write always fails, like a full disk."""

            def __init__(self, inner):
                self._inner = inner

            def write(self, _data):
                raise OSError("simulated write failure")

            def __getattr__(self, name):
                return getattr(self._inner, name)

            def __enter__(self):
                return self

            def __exit__(self, *_exc):
                self._inner.close()
                return False

        def flaky_fdopen(fd, mode="rb", *args, **kwargs):
            return _WriteBomb(real_fdopen(fd, mode, *args, **kwargs))

        monkeypatch.setattr(os, "fdopen", flaky_fdopen)
        with pytest.raises(OSError, match="write failure"):
            atomic_write_bytes(target, b"new-payload")

        assert target.read_bytes() == b"original"
        assert _siblings(root, target.name) == []

    def test_fsync_failure_cleans_tmp(self, tmp_path, monkeypatch):
        root = _fresh_dir(tmp_path)
        target = root / "state.bin"

        def boom(_fd):
            raise OSError("simulated fsync failure")

        monkeypatch.setattr(os, "fsync", boom)
        with pytest.raises(OSError, match="fsync failure"):
            atomic_write_bytes(target, b"payload")

        assert not target.exists()
        assert _siblings(root, target.name) == []


class TestModePinning:
    def test_mode_applied_on_fresh_write(self, tmp_path):
        root = _fresh_dir(tmp_path)
        target = root / "fresh.bin"
        atomic_write_bytes(target, b"x")
        assert (os.stat(target).st_mode & 0o777) == 0o644

    @pytest.mark.skipif(os.name == "nt", reason="POSIX mode bits differ")
    def test_mode_pinned_when_overwriting(self, tmp_path):
        root = _fresh_dir(tmp_path)
        target = root / "mode.bin"
        target.write_bytes(b"old")
        os.chmod(target, 0o777)
        atomic_write_bytes(target, b"new", mode=0o600)
        assert (os.stat(target).st_mode & 0o777) == 0o600
        atomic_write_bytes(target, b"newer", mode=0o644)
        assert (os.stat(target).st_mode & 0o777) == 0o644


class TestFsyncDirToggle:
    def test_fsync_dir_false_writes_correctly(self, tmp_path):
        root = _fresh_dir(tmp_path)
        target = root / "fast.bin"
        atomic_write_bytes(target, b"payload", fsync_dir=False)
        assert target.read_bytes() == b"payload"
        atomic_write_bytes(target, b"payload-2", fsync_dir=False)
        assert target.read_bytes() == b"payload-2"
        assert _siblings(root, target.name) == []


class TestAtomicWriteText:
    def test_text_roundtrip_unicode(self, tmp_path):
        root = _fresh_dir(tmp_path)
        target = root / "note.txt"
        atomic_write_text(target, "héllo wörld")
        assert target.read_text(encoding="utf-8") == "héllo wörld"


class TestAtomicWriteRoundTripOracle:
    @given(data=st.binary(max_size=8192))
    @settings(
        max_examples=60,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_write_then_read_roundtrip(self, data, tmp_path):
        root = _fresh_dir(tmp_path)
        target = root / "blob.bin"
        atomic_write_bytes(target, data)
        assert target.read_bytes() == data
        assert _siblings(root, target.name) == []

    @given(data=st.binary(max_size=1024))
    @settings(
        max_examples=40,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_overwrite_roundtrip(self, data, tmp_path):
        root = _fresh_dir(tmp_path)
        target = root / "blob.bin"
        target.write_bytes(b"stale")
        atomic_write_bytes(target, data)
        assert target.read_bytes() == data
