# SPDX-License-Identifier: 0BSD

"""Tests for profile permission hardening: umask, tighten pass, atomic writes, zip modes."""

from __future__ import annotations

import os
import stat
import sys
import zipfile

import pytest

from meshchatx.src.backend import profile_permissions
from meshchatx.src.backend.profile_permissions import (
    apply_process_umask,
    tighten_existing_profile,
)
from meshchatx.src.path_utils import atomic_write_bytes

pytestmark = pytest.mark.skipif(os.name == "nt", reason="POSIX permissions only")


def test_apply_process_umask_sets_077(monkeypatch):
    monkeypatch.delenv("MESHCHATX_NO_UMASK", raising=False)
    old = os.umask(0o022)
    try:
        apply_process_umask()
        assert os.umask(0) == 0o077
    finally:
        os.umask(old)


def test_apply_process_umask_opt_out(monkeypatch):
    monkeypatch.setenv("MESHCHATX_NO_UMASK", "1")
    old = os.umask(0o022)
    try:
        apply_process_umask()
        assert os.umask(0) == 0o022
    finally:
        os.umask(old)


def _mode(path):
    return stat.S_IMODE(os.lstat(path).st_mode)


def test_tighten_clears_group_other_keeps_owner(tmp_path):
    storage = tmp_path / "storage"
    (storage / "sub").mkdir(parents=True)
    target = storage / "sub" / "file.txt"
    target.write_text("x")
    os.chmod(target, 0o644)
    os.chmod(storage / "sub", 0o755)
    script = storage / "run.sh"
    script.write_text("#!/bin/sh\n")
    os.chmod(script, 0o755)

    tighten_existing_profile(str(storage), None)

    assert _mode(target) == 0o600
    assert _mode(storage / "sub") == 0o700
    assert _mode(script) == 0o700
    assert _mode(storage) == 0o700


def test_tighten_skips_symlinks(tmp_path):
    storage = tmp_path / "storage"
    outside = tmp_path / "outside.txt"
    storage.mkdir()
    outside.write_text("secret")
    os.chmod(outside, 0o644)
    link = storage / "link"
    link.symlink_to(outside)
    os.chmod(storage, 0o755)

    tighten_existing_profile(str(storage), None)

    assert _mode(outside) == 0o644, "symlink target outside storage must not change"
    assert stat.S_ISLNK(os.lstat(link).st_mode)


def test_tighten_marker_makes_idempotent(tmp_path, monkeypatch):
    storage = tmp_path / "storage"
    storage.mkdir()
    f = storage / "f"
    f.write_text("x")
    os.chmod(f, 0o644)
    tighten_existing_profile(str(storage), None)
    assert _mode(f) == 0o600

    calls = []
    real_chmod = os.chmod

    def spy(path, mode, *a, **kw):
        calls.append(path)
        return real_chmod(path, mode, *a, **kw)

    monkeypatch.setattr(os, "chmod", spy)
    tighten_existing_profile(str(storage), None)
    assert calls == [], "second run must no-op via marker"


def test_tighten_ignores_chmod_errors(tmp_path, monkeypatch):
    storage = tmp_path / "storage"
    storage.mkdir()
    f = storage / "f"
    f.write_text("x")
    os.chmod(f, 0o644)

    def boom(path, mode, *a, **kw):
        raise PermissionError("denied")

    monkeypatch.setattr(os, "chmod", boom)
    tighten_existing_profile(str(storage), None)  # must not raise
    assert (storage / profile_permissions._TIGHTEN_MARKER).exists()


def test_tighten_reticulum_config_only_owned(tmp_path, monkeypatch):
    storage = tmp_path / "storage"
    rns = tmp_path / "rns"
    (rns / "storage").mkdir(parents=True)
    storage.mkdir()
    priv = rns / "storage" / "transport_identity"
    priv.write_text("key")
    os.chmod(priv, 0o644)
    cfg = rns / "config"
    cfg.write_text("cfg")
    os.chmod(cfg, 0o644)
    public = rns / "public_file"
    public.write_text("pub")
    os.chmod(public, 0o644)

    tighten_existing_profile(str(storage), str(rns))

    assert _mode(priv) == 0o600
    assert _mode(cfg) == 0o600
    assert _mode(public) == 0o644, "files outside config/storage stay untouched"


def test_tighten_skipped_on_windows(monkeypatch, tmp_path):
    monkeypatch.setattr(os, "name", "nt")
    storage = tmp_path / "storage"
    storage.mkdir()
    tighten_existing_profile(str(storage), None)
    assert not (storage / profile_permissions._TIGHTEN_MARKER).exists()


def test_atomic_write_bytes_defaults_0600(tmp_path):
    target = tmp_path / "out.bin"
    atomic_write_bytes(target, b"data")
    assert _mode(target) == 0o600


def test_atomic_write_bytes_explicit_mode_kept(tmp_path):
    target = tmp_path / "shared.bin"
    atomic_write_bytes(target, b"data", mode=0o644)
    assert _mode(target) == 0o644


def _zip_with_mode(path, member, data, mode):
    with zipfile.ZipFile(path, "w") as zf:
        info = zipfile.ZipInfo(member)
        info.external_attr = (mode & 0o7777) << 16
        zf.writestr(info, data)


def test_safe_zip_extract_sanitizes_mode_bits(tmp_path):
    from meshchatx.src.backend.database import Database

    zip_path = tmp_path / "in.zip"
    _zip_with_mode(str(zip_path), "evil.sh", b"#!/bin/sh\n", 0o4755)
    target = tmp_path / "out"
    target.mkdir()

    with zipfile.ZipFile(zip_path) as zf:
        for member in zf.namelist():
            Database._safe_zip_extract_member(zf, member, str(target))

    extracted = target / "evil.sh"
    assert extracted.exists()
    mode = _mode(extracted)
    assert mode == 0o700, f"expected owner-rwx only, got {oct(mode)}"
    assert not mode & 0o6000, "setuid/setgid must be stripped"


def test_sqlite_sidecars_0600_under_umask_077(tmp_path):
    if sys.platform == "win32":
        pytest.skip("POSIX only")
    old = os.umask(0o077)
    try:
        db_path = tmp_path / "t.db"
        import sqlite3

        conn = sqlite3.connect(str(db_path))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("CREATE TABLE t (x)")
        conn.execute("INSERT INTO t VALUES (1)")
        conn.commit()
        conn.close()
    finally:
        os.umask(old)

    for suffix in ("", "-wal", "-shm"):
        p = tmp_path / f"t.db{suffix}"
        if p.exists():
            assert _mode(p) == 0o600, f"{p.name} mode {oct(_mode(p))}"
