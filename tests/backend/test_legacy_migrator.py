# SPDX-License-Identifier: 0BSD

import os
import shutil
import sqlite3
import stat
import tempfile
from pathlib import Path

import pytest
import RNS
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from meshchatx.src.backend.legacy_migrator import (
    CURRENT_DIR,
    LEGACY_DIR,
    assert_migration_context_paths,
    copy_legacy_storage_tree,
    fresh_storage_at_target,
    migrate_legacy_to_target,
    paired_legacy_from_new,
    paired_new_from_legacy,
    resolve_startup_storage,
    storage_has_meshchat_data,
)


def test_paired_paths():
    newp = os.path.join("/tmp", "x", CURRENT_DIR)
    assert paired_legacy_from_new(newp) == os.path.join("/tmp", "x", LEGACY_DIR)
    leg = os.path.join("/a", LEGACY_DIR)
    assert paired_new_from_legacy(leg) == os.path.join("/a", CURRENT_DIR)
    assert paired_legacy_from_new("/tmp/storage") is None


@pytest.mark.parametrize(
    "new_path",
    [
        os.path.join("/tmp", "p", CURRENT_DIR),
        os.path.join("/tmp", "p", CURRENT_DIR + os.sep),
    ],
)
def test_paired_legacy_trailing_slash_invariant(new_path):
    leg = paired_legacy_from_new(new_path)
    assert leg is not None
    assert os.path.basename(os.path.normpath(leg)) == LEGACY_DIR


@pytest.mark.parametrize("wrong_base", ["storage", ".meshchat", CURRENT_DIR + "x"])
def test_paired_none_for_wrong_basename(wrong_base):
    p = os.path.join("/tmp", "z", wrong_base)
    assert paired_legacy_from_new(p) is None
    assert paired_new_from_legacy(p) is None


def test_storage_has_meshchat_data_identity(tmp_path):
    ident = tmp_path / "identity"
    ident.write_bytes(b"x")
    assert storage_has_meshchat_data(str(tmp_path)) is True


def test_storage_has_meshchat_data_identities_db(tmp_path):
    dbdir = tmp_path / "identities" / "abc"
    dbdir.mkdir(parents=True)
    (dbdir / "database.db").write_text("x")
    assert storage_has_meshchat_data(str(tmp_path)) is True


@pytest.mark.parametrize(
    "setup",
    [
        "nonexistent",
        "empty_identity",
        "zero_byte_identity",
        "identities_no_db",
        "identities_empty",
        "not_a_directory",
    ],
)
def test_storage_has_meshchat_data_negative(tmp_path, setup):
    if setup == "nonexistent":
        assert storage_has_meshchat_data(str(tmp_path / "nope")) is False
        return
    if setup == "empty_identity":
        (tmp_path / "identity").write_text("")
        assert storage_has_meshchat_data(str(tmp_path)) is False
        return
    if setup == "zero_byte_identity":
        (tmp_path / "identity").write_bytes(b"")
        assert storage_has_meshchat_data(str(tmp_path)) is False
        return
    if setup == "identities_no_db":
        (tmp_path / "identities" / "h1").mkdir(parents=True)
        (tmp_path / "identities" / "h1" / "readme.txt").write_text("x")
        assert storage_has_meshchat_data(str(tmp_path)) is False
        return
    if setup == "identities_empty":
        (tmp_path / "identities").mkdir()
        assert storage_has_meshchat_data(str(tmp_path)) is False
        return
    if setup == "not_a_directory":
        (tmp_path / "identities").write_text("file")
        assert storage_has_meshchat_data(str(tmp_path)) is False


def test_storage_has_meshchat_data_empty_string():
    assert storage_has_meshchat_data("") is False


def test_resolve_redirect_when_new_empty_legacy_has_data(monkeypatch):
    root = tempfile.mkdtemp()
    try:
        new_home = os.path.join(root, CURRENT_DIR)
        leg_home = os.path.join(root, LEGACY_DIR)
        os.makedirs(leg_home, exist_ok=True)
        ident = os.path.join(leg_home, "identity")
        with open(ident, "wb") as f:
            f.write(RNS.Identity(create_keys=True).get_private_key())
        monkeypatch.delenv("MESHCHAT_SKIP_LEGACY_MIGRATION_UI", raising=False)
        eff, ctx = resolve_startup_storage(new_home)
        assert eff == leg_home
        assert ctx["show_choice"] is True
        assert ctx["target_path"] == new_home
        assert ctx["legacy_path"] == leg_home
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_resolve_new_has_identity_no_redirect(monkeypatch):
    root = tempfile.mkdtemp()
    try:
        new_home = os.path.join(root, CURRENT_DIR)
        leg_home = os.path.join(root, LEGACY_DIR)
        os.makedirs(new_home, exist_ok=True)
        os.makedirs(leg_home, exist_ok=True)
        with open(os.path.join(new_home, "identity"), "wb") as f:
            f.write(RNS.Identity(create_keys=True).get_private_key())
        with open(os.path.join(leg_home, "identity"), "wb") as f:
            f.write(RNS.Identity(create_keys=True).get_private_key())
        monkeypatch.delenv("MESHCHAT_SKIP_LEGACY_MIGRATION_UI", raising=False)
        eff, ctx = resolve_startup_storage(new_home)
        assert eff == os.path.abspath(new_home)
        assert ctx.get("show_choice") is not True
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_resolve_legacy_empty_no_prompt(monkeypatch):
    root = tempfile.mkdtemp()
    try:
        new_home = os.path.join(root, CURRENT_DIR)
        leg_home = os.path.join(root, LEGACY_DIR)
        os.makedirs(leg_home, exist_ok=True)
        monkeypatch.delenv("MESHCHAT_SKIP_LEGACY_MIGRATION_UI", raising=False)
        eff, ctx = resolve_startup_storage(new_home)
        assert eff == os.path.abspath(new_home)
        assert ctx.get("show_choice") is not True
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_resolve_on_legacy_path(monkeypatch):
    root = tempfile.mkdtemp()
    try:
        leg_home = os.path.join(root, LEGACY_DIR)
        os.makedirs(leg_home, exist_ok=True)
        ident = os.path.join(leg_home, "identity")
        with open(ident, "wb") as f:
            f.write(RNS.Identity(create_keys=True).get_private_key())
        monkeypatch.delenv("MESHCHAT_SKIP_LEGACY_MIGRATION_UI", raising=False)
        eff, ctx = resolve_startup_storage(leg_home)
        assert eff == leg_home
        assert ctx["show_choice"] is True
        assert ctx["target_path"] == os.path.join(root, CURRENT_DIR)
    finally:
        shutil.rmtree(root, ignore_errors=True)


@pytest.mark.parametrize("truthy", ("1", "true", "yes", "TRUE", " Yes "))
def test_resolve_skip_env_variants(monkeypatch, truthy):
    root = tempfile.mkdtemp()
    try:
        new_home = os.path.join(root, CURRENT_DIR)
        leg_home = os.path.join(root, LEGACY_DIR)
        os.makedirs(leg_home, exist_ok=True)
        with open(os.path.join(leg_home, "identity"), "wb") as f:
            f.write(RNS.Identity(create_keys=True).get_private_key())
        monkeypatch.setenv("MESHCHAT_SKIP_LEGACY_MIGRATION_UI", truthy)
        eff, ctx = resolve_startup_storage(new_home)
        assert eff == os.path.abspath(new_home)
        assert ctx.get("show_choice") is not True
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_resolve_relative_non_dot_name(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("MESHCHAT_SKIP_LEGACY_MIGRATION_UI", raising=False)
    eff, ctx = resolve_startup_storage("storage")
    assert eff == os.path.abspath(os.path.join(str(tmp_path), "storage"))
    assert ctx.get("show_choice") is not True


def test_migrate_and_fresh(tmp_path):
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    src.mkdir()
    (src / "identity").write_bytes(RNS.Identity(create_keys=True).get_private_key())
    sub = src / "identities" / "aa"
    sub.mkdir(parents=True)
    (sub / "database.db").write_text("db")
    migrate_legacy_to_target(str(src), str(dst))
    assert (dst / "identity").is_file()
    assert (dst / "identities" / "aa" / "database.db").read_text() == "db"
    fresh = tmp_path / "fresh"
    fresh_storage_at_target(str(fresh))
    assert (fresh / "identity").is_file()
    id2 = RNS.Identity(create_keys=False)
    id2.load(str(fresh / "identity"))
    assert id2.hash is not None


def test_migrate_rejects_nonempty_target(tmp_path):
    src = tmp_path / "s"
    dst = tmp_path / "d"
    src.mkdir()
    dst.mkdir()
    (src / "identity").write_bytes(RNS.Identity(create_keys=True).get_private_key())
    (dst / "identity").write_bytes(RNS.Identity(create_keys=True).get_private_key())
    with pytest.raises(ValueError):
        migrate_legacy_to_target(str(src), str(dst))


def test_fresh_rejects_nonempty_target(tmp_path):
    (tmp_path / "identity").write_bytes(
        RNS.Identity(create_keys=True).get_private_key()
    )
    with pytest.raises(ValueError):
        fresh_storage_at_target(str(tmp_path))


def test_assert_migration_context_paths():
    ctx = {
        "show_choice": True,
        "legacy_path": "/a/.reticulum-meshchat",
        "target_path": "/a/.reticulum-meshchatx",
    }
    assert_migration_context_paths(
        ctx, "/a/.reticulum-meshchat", "/a/.reticulum-meshchatx"
    )
    with pytest.raises(ValueError):
        assert_migration_context_paths(
            ctx, "/b/.reticulum-meshchat", "/a/.reticulum-meshchatx"
        )


def test_assert_migration_context_requires_show_choice():
    with pytest.raises(ValueError):
        assert_migration_context_paths({}, "/a/x", "/b/y")


def test_copy_rejects_same_path(tmp_path):
    one = tmp_path / "x"
    one.mkdir()
    with pytest.raises(ValueError):
        copy_legacy_storage_tree(str(one), str(one))


def test_copy_rejects_missing_source(tmp_path):
    with pytest.raises(ValueError):
        copy_legacy_storage_tree(str(tmp_path / "missing"), str(tmp_path / "dst"))


def test_copy_skips_pycache_and_pyc(tmp_path):
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    (src / "__pycache__").mkdir(parents=True)
    (src / "__pycache__" / "x.pyc").write_bytes(b"1")
    (src / "keep.txt").write_text("ok")
    (src / "bad.pyc").write_bytes(b"2")
    copy_legacy_storage_tree(str(src), str(dst))
    assert (dst / "keep.txt").read_text() == "ok"
    assert not (dst / "__pycache__").exists()
    assert not (dst / "bad.pyc").exists()


def test_copy_preserves_mode_bits(tmp_path):
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    src.mkdir()
    exe = src / "run.sh"
    exe.write_text("#!/bin/sh\necho hi\n")
    os.chmod(exe, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
    copy_legacy_storage_tree(str(src), str(dst))
    st = os.stat(dst / "run.sh")
    assert stat.S_IMODE(st.st_mode) & stat.S_IXUSR


@pytest.mark.skipif(os.name == "nt", reason="symlink semantics differ on Windows")
def test_copy_symlink_file(tmp_path):
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    src.mkdir()
    real = src / "data.bin"
    real.write_bytes(b"\x00\x01")
    link = src / "link.bin"
    link.symlink_to("data.bin")
    copy_legacy_storage_tree(str(src), str(dst))
    assert (dst / "link.bin").is_symlink()
    assert os.readlink(dst / "link.bin") == "data.bin"


def test_migrate_unicode_path_segment(tmp_path):
    seg = "caf\u00e9-\u4e01"
    src = tmp_path / seg / "src"
    dst = tmp_path / seg / "dst"
    src.mkdir(parents=True)
    (src / "identity").write_bytes(RNS.Identity(create_keys=True).get_private_key())
    migrate_legacy_to_target(str(src), str(dst))
    assert (dst / "identity").is_file()


@settings(
    max_examples=60,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(
    suffix=st.text(
        alphabet=st.characters(min_codepoint=ord("a"), max_codepoint=ord("z")),
        min_size=1,
        max_size=20,
    ),
)
def test_paired_paths_roundtrip_hypothesis(tmp_path, suffix):
    parent = str(tmp_path / suffix)
    os.makedirs(parent, exist_ok=True)
    newp = os.path.join(parent, CURRENT_DIR)
    leg = paired_legacy_from_new(newp)
    assert leg is not None
    assert paired_new_from_legacy(leg) == os.path.normpath(newp)


def _create_old_meshchat_style_sqlite(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript(
            """
            CREATE TABLE config (
                id INTEGER NOT NULL PRIMARY KEY,
                key VARCHAR(255) NOT NULL UNIQUE,
                value TEXT NOT NULL
            );
            CREATE TABLE lxmf_messages (
                id INTEGER NOT NULL PRIMARY KEY,
                hash VARCHAR(255) NOT NULL UNIQUE,
                source_hash VARCHAR(255) NOT NULL,
                destination_hash VARCHAR(255) NOT NULL,
                state VARCHAR(255) NOT NULL,
                progress REAL NOT NULL DEFAULT 0
            );
            CREATE TABLE announces (
                id INTEGER NOT NULL PRIMARY KEY,
                destination_hash VARCHAR(255) NOT NULL UNIQUE,
                aspect TEXT NOT NULL,
                identity_hash VARCHAR(255) NOT NULL,
                identity_public_key VARCHAR(255) NOT NULL,
                app_data TEXT
            );
            INSERT INTO config (key, value) VALUES ('database_version', '5');
            INSERT INTO lxmf_messages (hash, source_hash, destination_hash, state, progress)
            VALUES ('msghex01', 'src01', 'dst01', 'delivered', 1.0);
            INSERT INTO announces (destination_hash, aspect, identity_hash, identity_public_key, app_data)
            VALUES ('dh01', 'lxmf.delivery', 'ih01', 'pk01', NULL);
            """
        )
        conn.commit()
    finally:
        conn.close()


def _sqlite_integrity_ok(db_path: Path) -> bool:
    conn = sqlite3.connect(str(db_path))
    try:
        row = conn.execute("PRAGMA integrity_check").fetchone()
        return row is not None and row[0] == "ok"
    finally:
        conn.close()


def test_live_migrate_sqlite_meshchat_like_database(tmp_path):
    legacy_root = tmp_path / "legacy_layout"
    legacy_root.mkdir()
    ident_path = legacy_root / "identity"
    ident_path.write_bytes(RNS.Identity(create_keys=True).get_private_key())
    id_hash = "a1b2c3d4e5f6789012345678abcdef"
    db_path = legacy_root / "identities" / id_hash / "database.db"
    _create_old_meshchat_style_sqlite(db_path)

    target_root = tmp_path / "target_layout"
    migrate_legacy_to_target(str(legacy_root), str(target_root))

    migrated_db = target_root / "identities" / id_hash / "database.db"
    assert migrated_db.is_file()
    assert _sqlite_integrity_ok(migrated_db)
    conn = sqlite3.connect(str(migrated_db))
    try:
        n = conn.execute("SELECT COUNT(*) FROM lxmf_messages").fetchone()[0]
        assert n == 1
        h = conn.execute("SELECT hash FROM lxmf_messages LIMIT 1").fetchone()[0]
        assert h == "msghex01"
        ac = conn.execute("SELECT COUNT(*) FROM announces").fetchone()[0]
        assert ac == 1
    finally:
        conn.close()
    assert ident_path.read_bytes() == (target_root / "identity").read_bytes()


def test_live_migrate_copies_wal_sidecar_files(tmp_path):
    legacy_root = tmp_path / "wal_src"
    legacy_root.mkdir()
    (legacy_root / "identity").write_bytes(
        RNS.Identity(create_keys=True).get_private_key()
    )
    db_path = legacy_root / "identities" / "idwal" / "database.db"
    _create_old_meshchat_style_sqlite(db_path)
    src_dir = db_path.parent
    before = {p.name for p in src_dir.iterdir()}

    target_root = tmp_path / "wal_dst"
    migrate_legacy_to_target(str(legacy_root), str(target_root))
    tdb = target_root / "identities" / "idwal" / "database.db"
    assert tdb.is_file()
    after = {p.name for p in tdb.parent.iterdir()}
    assert before == after
    assert _sqlite_integrity_ok(tdb)


def test_resolve_identities_only_no_root_identity(monkeypatch):
    root = tempfile.mkdtemp()
    try:
        new_home = os.path.join(root, CURRENT_DIR)
        leg_home = os.path.join(root, LEGACY_DIR)
        os.makedirs(os.path.join(leg_home, "identities", "abc"), exist_ok=True)
        dbp = os.path.join(leg_home, "identities", "abc", "database.db")
        _create_old_meshchat_style_sqlite(Path(dbp))
        monkeypatch.delenv("MESHCHAT_SKIP_LEGACY_MIGRATION_UI", raising=False)
        eff, ctx = resolve_startup_storage(new_home)
        assert eff == leg_home
        assert ctx["show_choice"] is True
    finally:
        shutil.rmtree(root, ignore_errors=True)
