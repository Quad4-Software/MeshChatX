# SPDX-License-Identifier: 0BSD

"""Property, oracle, adversarial, and metamorphic tests for the translation pack manager.

These tests use independent oracles (path containment, regex invariants, round-trip
identity) rather than example-based soft assertions. They are designed to catch
jailbreaks, traversal, and partial-installation bugs that example tests can miss.
"""

import shutil
import uuid

import io
import json
import os
import tarfile
import zipfile
from pathlib import Path

import pytest
from hypothesis import HealthCheck, example, given, settings, strategies as st

from meshchatx.src.backend.translation_pack_manager import (
    TranslationPackError,
    TranslationPackManager,
    _ALLOWED_FILE_NAME_RE,
    _FILE_TYPE_RE,
    _PAIR_CODE_RE,
    _REQUIRED_PARTS,
)


_ALPHABET = "abcdefghijklmnopqrstuvwxyz"
_ALLOWED_NAME_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.@- "
_PARTS = ["model", "lex", "vocab", "qualityModel", "srcvocab", "trgvocab"]
_REQUIRED = set(_REQUIRED_PARTS)


def _independent_pair_match(s):
    try:
        s.encode("ascii")
    except UnicodeEncodeError:
        return False
    return len(s) == 4 and s.isalpha()


def _independent_filename_rejected(s):
    """Independent oracle: a filename is unsafe if it is empty, ., .., hidden, or
    contains a path-separator-like or drive-letter character."""
    if not s:
        return True
    if s in (".", ".."):
        return True
    if s.startswith("."):
        return True
    if "\x00" in s or "/" in s or "\\" in s or ":" in s:
        return True
    return False


def _make_zip(path, entries):
    with zipfile.ZipFile(path, "w") as zf:
        for name, data, _ in entries:
            zf.writestr(name, data)


def _make_tar(path, entries, mode="w"):
    with tarfile.open(path, mode) as tf:
        for name, data, kind in entries:
            if kind == "symlink":
                info = tarfile.TarInfo(name)
                info.type = tarfile.SYMTYPE
                info.linkname = data.decode("utf-8", errors="replace") if isinstance(data, bytes) else str(data)
                tf.addfile(info)
            else:
                info = tarfile.TarInfo(name)
                data = data if isinstance(data, bytes) else data.encode("utf-8")
                info.size = len(data)
                tf.addfile(info, io.BytesIO(data))


def _make_archive(path, entries, kind):
    if kind == "zip":
        _make_zip(path, entries)
    elif kind == "tar:gz":
        _make_tar(path, entries, mode="w:gz")
    else:
        _make_tar(path, entries, mode="w")


@st.composite
def pair_code(draw):
    return "".join(draw(st.lists(st.sampled_from(_ALPHABET), min_size=4, max_size=4)))


@st.composite
def pack_entries(draw, include_garbage=True, include_symlinks=True):
    """Generate a list of archive entries. Always includes the three required parts
    plus random adversarial extras."""
    pair = draw(pair_code())
    entries = []
    for part in _REQUIRED_PARTS:
        suffix = draw(st.sampled_from([".npz", ".bin", ".spm", ".s2t.bin", ".en-es.npz"]))
        body = draw(st.text(alphabet=_ALLOWED_NAME_CHARS, min_size=1, max_size=20))
        # _FILE_TYPE_RE requires the part name followed by a non-alphanumeric char.
        filename = f"{pair}/{part}.{body}{suffix}"
        data = draw(st.binary(min_size=1, max_size=1024))
        entries.append((filename, data, "file"))

    if include_garbage:
        n_extras = draw(st.integers(min_value=0, max_value=4))
        for _ in range(n_extras):
            name = draw(st.text(alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd")), min_size=1, max_size=20))
            data = draw(st.binary(min_size=0, max_size=128))
            # Half the time generate a benign extra, half the time an adversarial path.
            if draw(st.booleans()):
                entries.append((f"{pair}/{name}.txt", data, "file"))
            else:
                adversarial = draw(st.sampled_from([
                    f"{pair}/../{name}.txt",
                    f"../{name}.txt",
                    f"/{pair}/{name}.txt",
                    f"{pair}\\..\\{name}.txt",
                    f"..\\{name}.txt",
                ]))
                entries.append((adversarial, data, "file"))

    if include_symlinks:
        n_links = draw(st.integers(min_value=0, max_value=2))
        for _ in range(n_links):
            name = draw(st.text(alphabet=_ALPHABET, min_size=2, max_size=8))
            target = draw(st.text(alphabet=_ALPHABET, min_size=2, max_size=8))
            # Symlinks are only meaningful in tar; the helper encodes target as bytes.
            entries.append((f"{pair}/{name}.npz", target.encode(), "symlink"))

    return entries


@st.composite
def archive_kind(draw):
    return draw(st.sampled_from(["zip", "tar", "tar:gz"]))


class TestPackManagerRegexOracles:
    @given(s=st.text())
    @settings(max_examples=200, deadline=None)
    def test_pair_code_matches_alphabetic_four(self, s):
        match = bool(_PAIR_CODE_RE.match(s))
        oracle = _independent_pair_match(s)
        assert match == oracle

    @given(s=st.text())
    @example(s="")
    @example(s=".")
    @example(s="..")
    @example(s=".hidden")
    @example(s="foo\x00bar")
    @example(s="foo/bar")
    @example(s="foo\\bar")
    @example(s="C:foo")
    @settings(max_examples=200, deadline=None)
    def test_allowed_filename_rejects_dangerous_names(self, s):
        if _independent_filename_rejected(s):
            assert _ALLOWED_FILE_NAME_RE.match(s) is None


class TestPackManagerJailOracles:
    @given(p=st.text())
    @example(p="enes/model.npz")
    @example(p="enes/../model.npz")
    @example(p="../evil.txt")
    @example(p="/etc/passwd")
    @example(p="foo\\..\\bar")
    @example(p="foo\x00bar")
    @settings(max_examples=200, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_safe_file_path_never_escapes_packs_dir(self, p, tmp_path):
        root = tmp_path / str(uuid.uuid4())
        root.mkdir()
        mgr = TranslationPackManager(str(root))
        result = mgr.safe_file_path(p)
        if result is None:
            return
        packs_dir = Path(mgr.packs_dir).resolve()
        resolved = Path(result).resolve()
        assert resolved.is_relative_to(packs_dir)
        assert os.path.isfile(result)

    @given(entries=pack_entries(), kind=archive_kind())
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_imported_files_stay_under_packs_dir(self, entries, kind, tmp_path):
        root = tmp_path / str(uuid.uuid4())
        root.mkdir()
        archive_path = root / ("pack.tar" if kind.startswith("tar") else "pack.zip")
        _make_archive(str(archive_path), entries, kind)
        mgr = TranslationPackManager(str(root))

        try:
            mgr.import_archive(str(archive_path))
        except TranslationPackError:
            pass

        packs_dir = Path(mgr.packs_dir).resolve()
        for walk_root, _dirs, files in os.walk(mgr.packs_dir):
            for f in files:
                resolved = Path(os.path.join(walk_root, f)).resolve()
                assert resolved.is_relative_to(packs_dir)

        # No extracted file may exist outside the packs directory.
        archive_names = {"pack.tar", "pack.zip", "pack.tar.gz", "pack.tgz"}
        for walk_root, _dirs, files in os.walk(str(root)):
            for f in files:
                resolved = Path(os.path.join(walk_root, f)).resolve()
                if resolved.is_relative_to(packs_dir):
                    continue
                if f in archive_names or resolved.name in archive_names:
                    continue
                assert False, f"unexpected file outside packs_dir: {resolved}"


class TestPackManagerMetamorphicOracles:
    @given(entries=pack_entries(include_garbage=False, include_symlinks=False), kind=archive_kind())
    @settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_import_remove_import_is_idempotent(self, entries, kind, tmp_path):
        root = tmp_path / str(uuid.uuid4())
        root.mkdir()
        archive_path = root / ("pack.tar" if kind.startswith("tar") else "pack.zip")
        archive_copy = root / ("pack2.tar" if kind.startswith("tar") else "pack2.zip")
        _make_archive(str(archive_path), entries, kind)
        shutil.copy(str(archive_path), str(archive_copy))
        mgr = TranslationPackManager(str(root))

        pairs = mgr.import_archive(str(archive_path))
        if not pairs:
            return
        first = [dict(p) for p in mgr.list_installed()]

        for pair in pairs:
            assert mgr.remove_pack(pair) is True
        assert mgr.list_installed() == []

        pairs2 = mgr.import_archive(str(archive_copy))
        assert sorted(pairs2) == sorted(pairs)
        second = [dict(p) for p in mgr.list_installed()]

        # Normalise order-independent fields before comparing.
        for snapshot in (first, second):
            for pack in snapshot:
                pack["files"] = sorted(pack["files"])
        assert first == second

    @given(entries=pack_entries(include_garbage=False, include_symlinks=False))
    @settings(max_examples=20, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_zip_and_tar_imports_agree(self, entries, tmp_path):
        root = tmp_path / str(uuid.uuid4())
        root.mkdir()
        zip_path = root / "pack.zip"
        tar_path = root / "pack.tar"
        _make_zip(str(zip_path), entries)
        _make_tar(str(tar_path), entries)

        mgr_zip = TranslationPackManager(str(root / "zip"))
        mgr_tar = TranslationPackManager(str(root / "tar"))

        pairs_zip = mgr_zip.import_archive(str(zip_path))
        pairs_tar = mgr_tar.import_archive(str(tar_path))
        assert sorted(pairs_zip) == sorted(pairs_tar)

        for zip_pack, tar_pack in zip(
            sorted(mgr_zip.list_installed(), key=lambda p: p["pair"]),
            sorted(mgr_tar.list_installed(), key=lambda p: p["pair"]),
        ):
            assert zip_pack["from"] == tar_pack["from"]
            assert zip_pack["to"] == tar_pack["to"]
            assert sorted(zip_pack["files"]) == sorted(tar_pack["files"])


class TestPackManagerAdversarialOracles:
    @pytest.mark.parametrize(
        "entries,expected_outside",
        [
            (
                [
                    ("../evil.txt", b"evil", "file"),
                    ("enes/model.npz", b"m", "file"),
                    ("enes/lex.s2t.bin", b"l", "file"),
                    ("enes/vocab.spm", b"v", "file"),
                ],
                "evil.txt",
            ),
            (
                [
                    ("/etc/passwd", b"root", "file"),
                    ("enes/model.npz", b"m", "file"),
                    ("enes/lex.s2t.bin", b"l", "file"),
                    ("enes/vocab.spm", b"v", "file"),
                ],
                "etc",
            ),
            (
                [
                    ("..\\evil.txt", b"evil", "file"),
                    ("enes/model.npz", b"m", "file"),
                    ("enes/lex.s2t.bin", b"l", "file"),
                    ("enes/vocab.spm", b"v", "file"),
                ],
                "evil.txt",
            ),
        ],
    )
    def test_zip_traversal_does_not_escape(self, entries, expected_outside, tmp_path):
        archive = tmp_path / "pack.zip"
        _make_zip(str(archive), entries)
        mgr = TranslationPackManager(str(tmp_path))
        pairs = mgr.import_archive(str(archive))
        assert pairs == ["enes"]
        assert not os.path.exists(os.path.join(tmp_path, expected_outside))
        assert not os.path.exists(os.path.join(mgr.packs_dir, expected_outside))
