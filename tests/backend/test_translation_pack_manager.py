# SPDX-License-Identifier: 0BSD

"""Tests for the local translation pack manager."""

import io
import json
import os
import tarfile
import zipfile

import pytest

from meshchatx.src.backend.translation_pack_manager import TranslationPackError, TranslationPackManager


def _make_zip(tmp_path, entries):
    archive = tmp_path / "pack.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
    return archive


def test_manager_creates_pack_directories(tmp_path):
    mgr = TranslationPackManager(str(tmp_path))
    assert os.path.isdir(mgr.packs_dir)
    assert os.path.isdir(mgr.incoming_dir)
    assert mgr.list_installed() == []


def test_import_single_pair_zip(tmp_path):
    mgr = TranslationPackManager(str(tmp_path))
    entries = {
        "enes/model.enes.npz": b"model",
        "enes/lex.50.50.enes.s2t.bin": b"lex",
        "enes/vocab.enes.spm": b"vocab",
    }
    archive = _make_zip(tmp_path, entries)
    pairs = mgr.import_archive(str(archive))
    assert pairs == ["enes"]
    installed = mgr.list_installed()
    assert len(installed) == 1
    assert installed[0]["pair"] == "enes"
    assert installed[0]["from"] == "en"
    assert installed[0]["to"] == "es"
    assert set(installed[0]["files"]) == {"model", "lex", "vocab"}
    assert os.path.isfile(mgr.safe_file_path("enes/model.enes.npz"))


def test_import_with_pack_json(tmp_path):
    mgr = TranslationPackManager(str(tmp_path))
    pack = {
        "id": "deen",
        "from": "de",
        "to": "en",
        "version": "1.0",
        "files": {
            "model": {"name": "model.deen.npz"},
            "lex": {"name": "lex.deen.s2t.bin"},
            "vocab": {"name": "vocab.deen.spm"},
        },
    }
    entries = {
        "pack.json": json.dumps(pack),
        "deen/model.deen.npz": b"model",
        "deen/lex.deen.s2t.bin": b"lex",
        "deen/vocab.deen.spm": b"vocab",
    }
    archive = _make_zip(tmp_path, entries)
    pairs = mgr.import_archive(str(archive))
    assert pairs == ["deen"]
    installed = {p["pair"]: p for p in mgr.list_installed()}
    assert installed["deen"]["version"] == "1.0"


def test_import_registry_json(tmp_path):
    mgr = TranslationPackManager(str(tmp_path))
    registry = {
        "enes": {
            "from": "en",
            "to": "es",
            "files": {
                "model": {"name": "model.npz"},
                "lex": {"name": "lex.s2t.bin"},
                "vocab": {"name": "vocab.spm"},
            },
        },
        "fren": {
            "from": "fr",
            "to": "en",
            "files": {
                "model": {"name": "model.npz"},
                "lex": {"name": "lex.s2t.bin"},
                "vocab": {"name": "vocab.spm"},
            },
        },
    }
    entries = {
        "registry.json": json.dumps(registry),
        "enes/model.npz": b"m1",
        "enes/lex.s2t.bin": b"l1",
        "enes/vocab.spm": b"v1",
        "fren/model.npz": b"m2",
        "fren/lex.s2t.bin": b"l2",
        "fren/vocab.spm": b"v2",
    }
    archive = _make_zip(tmp_path, entries)
    pairs = mgr.import_archive(str(archive))
    assert sorted(pairs) == ["enes", "fren"]
    assert len(mgr.list_installed()) == 2


def test_import_rejects_path_traversal(tmp_path):
    mgr = TranslationPackManager(str(tmp_path))
    entries = {
        "../evil.txt": b"evil",
        "enes/model.npz": b"model",
        "enes/lex.s2t.bin": b"lex",
        "enes/vocab.spm": b"vocab",
    }
    archive = _make_zip(tmp_path, entries)
    pairs = mgr.import_archive(str(archive))
    assert pairs == ["enes"]
    assert not os.path.exists(tmp_path / "evil.txt")


def test_import_rejects_missing_required_files(tmp_path):
    mgr = TranslationPackManager(str(tmp_path))
    entries = {"enes/model.npz": b"model"}
    archive = _make_zip(tmp_path, entries)
    with pytest.raises(TranslationPackError):
        mgr.import_archive(str(archive))


def test_remove_pack(tmp_path):
    mgr = TranslationPackManager(str(tmp_path))
    _make_zip(tmp_path, {
        "enes/model.npz": b"model",
        "enes/lex.s2t.bin": b"lex",
        "enes/vocab.spm": b"vocab",
    })
    mgr.import_archive(str(tmp_path / "pack.zip"))
    assert mgr.list_installed()
    assert mgr.remove_pack("enes") is True
    assert mgr.list_installed() == []
    assert mgr.remove_pack("enes") is False
    assert mgr.remove_pack("bad") is False


def test_safe_file_path_blocks_traversal(tmp_path):
    mgr = TranslationPackManager(str(tmp_path))
    assert mgr.safe_file_path("../etc/passwd") is None
    assert mgr.safe_file_path("/etc/passwd") is None
    assert mgr.safe_file_path("foo\x00bar") is None
    assert mgr.safe_file_path("foo\\..\\bar") is None


def _make_tar(tmp_path, entries):
    archive = tmp_path / "pack.tar"
    with tarfile.open(archive, "w") as tf:
        for name, data in entries.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tf.addfile(info, io.BytesIO(data))
    return archive


def test_import_rejects_absolute_zip_entry(tmp_path):
    mgr = TranslationPackManager(str(tmp_path))
    entries = {
        "/etc/evil.txt": b"evil",
        "enes/model.npz": b"model",
        "enes/lex.s2t.bin": b"lex",
        "enes/vocab.spm": b"vocab",
    }
    archive = _make_zip(tmp_path, entries)
    pairs = mgr.import_archive(str(archive))
    assert pairs == ["enes"]
    assert not os.path.exists(tmp_path / "etc" / "evil.txt")


def test_import_rejects_symlink_and_hardlink_in_tar(tmp_path):
    mgr = TranslationPackManager(str(tmp_path))
    archive = tmp_path / "pack.tar"
    with tarfile.open(archive, "w") as tf:
        data = b"target"
        info = tarfile.TarInfo("enes/target.txt")
        info.size = len(data)
        tf.addfile(info, io.BytesIO(data))

        sym = tarfile.TarInfo("enes/model.npz")
        sym.type = tarfile.SYMTYPE
        sym.linkname = "target.txt"
        tf.addfile(sym)

        lnk = tarfile.TarInfo("enes/lex.s2t.bin")
        lnk.type = tarfile.LNKTYPE
        lnk.linkname = "target.txt"
        tf.addfile(lnk)

        info = tarfile.TarInfo("enes/vocab.spm")
        info.size = 5
        tf.addfile(info, io.BytesIO(b"vocab"))
    with pytest.raises(TranslationPackError):
        mgr.import_archive(str(archive))


def test_import_rejects_dotdot_in_tar_member(tmp_path):
    mgr = TranslationPackManager(str(tmp_path))
    entries = {
        "enes/ok.txt": b"ok",
        "enes/../evil.txt": b"evil",
        "enes/model.npz": b"model",
        "enes/lex.s2t.bin": b"lex",
        "enes/vocab.spm": b"vocab",
    }
    archive = _make_tar(tmp_path, entries)
    pairs = mgr.import_archive(str(archive))
    assert pairs == ["enes"]
    assert not os.path.exists(tmp_path / "evil.txt")


def test_import_rejects_hidden_files(tmp_path):
    mgr = TranslationPackManager(str(tmp_path))
    entries = {
        "enes/.hidden": b"hidden",
        "enes/model.npz": b"model",
        "enes/lex.s2t.bin": b"lex",
        "enes/vocab.spm": b"vocab",
    }
    archive = _make_zip(tmp_path, entries)
    pairs = mgr.import_archive(str(archive))
    assert pairs == ["enes"]
    assert not os.path.exists(os.path.join(mgr.packs_dir, "enes", ".hidden"))


def test_import_registry_sets_file_sizes(tmp_path):
    mgr = TranslationPackManager(str(tmp_path))
    registry = {
        "enes": {
            "from": "en",
            "to": "es",
            "files": {
                "model": {"name": "model.npz"},
                "lex": {"name": "lex.s2t.bin"},
                "vocab": {"name": "vocab.spm"},
            },
        },
    }
    entries = {
        "registry.json": json.dumps(registry),
        "enes/model.npz": b"m" * 100,
        "enes/lex.s2t.bin": b"l" * 50,
        "enes/vocab.spm": b"v" * 25,
    }
    archive = _make_zip(tmp_path, entries)
    pairs = mgr.import_archive(str(archive))
    assert pairs == ["enes"]
    installed = {p["pair"]: p for p in mgr.list_installed()}
    assert installed["enes"]["size"] == 175
