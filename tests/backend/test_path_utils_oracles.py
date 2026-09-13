# SPDX-License-Identifier: 0BSD

"""Property-based and adversarial oracles for meshchatx/src/path_utils.py."""

import os
import uuid
from typing import ClassVar

import pytest
from hypothesis import HealthCheck, example, given, settings
from hypothesis import strategies as st

from meshchatx.src.path_utils import (
    PathJailError,
    first_component_under,
    is_direct_child,
    is_path_within_dir,
    is_safe_archive_member,
    is_under_root,
    normalize_relpath,
    realpath_or_none,
    relative_to_root,
    request_client_ip,
    resolve_path_under_dir,
    resolve_under_root,
    resolve_user_path,
    safe_basename,
    safe_path_under_dir,
)

_NAME_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-"
_SAFE_NAME = st.text(alphabet=_NAME_ALPHABET, min_size=1, max_size=24)


@st.composite
def safe_segment(draw):
    name = draw(_SAFE_NAME)
    suffix = draw(st.sampled_from(["", ".txt", ".bin", ".npz", ".dir"]))
    return name + suffix


@st.composite
def safe_relative_path(draw):
    segments = draw(st.lists(safe_segment(), min_size=1, max_size=4))
    return "/".join(segments)


@st.composite
def adversarial_path(draw):
    return draw(
        st.one_of(
            st.text(),
            st.sampled_from(
                [
                    "",
                    ".",
                    "..",
                    ".hidden",
                    "../evil.txt",
                    "../../etc/passwd",
                    "/etc/passwd",
                    "C:boot.ini",
                    "foo\\..\\bar",
                    "foo\x00bar",
                    "foo/bar/../baz",
                    "foo/../..",
                    "//double",
                ]
            ),
        )
    )


class TestPathWithinDirOracle:
    @given(user_path=adversarial_path(), directory=adversarial_path())
    @example(user_path="/etc/passwd", directory="/tmp/root")
    @example(user_path="../outside", directory="/tmp/root")
    @example(user_path="foo/bar", directory="/tmp/root")
    @settings(
        max_examples=150,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_is_path_within_dir_never_returns_true_for_outside(
        self, user_path, directory, tmp_path
    ):
        # Construct stable on-disk roots so realpath does not depend on cwd.
        root = tmp_path / str(uuid.uuid4())
        root.mkdir()
        # Resolve a real directory outside root.
        outside = tmp_path / str(uuid.uuid4())
        outside.mkdir()

        if directory in ("", "."):
            directory = str(root)
        elif not os.path.isabs(directory):
            directory = str(root)
        else:
            # If the generated directory is absolute, replace with an outside path.
            directory = str(outside)

        if not user_path or "\x00" in user_path:
            user_path = "valid"

        full = os.path.join(directory, user_path.replace("\\", "/"))
        result = is_path_within_dir(full, str(root))
        if result:
            resolved = os.path.realpath(full)
            root_resolved = os.path.realpath(str(root))
            assert resolved == root_resolved or resolved.startswith(
                root_resolved + os.sep
            )


class TestSafePathUnderDirOracle:
    @given(filename=st.text())
    @example(filename="")
    @example(filename=".")
    @example(filename="..")
    @example(filename=".hidden")
    @example(filename="foo\x00bar")
    @example(filename="foo/bar")
    @example(filename="C:evil")
    @example(filename="foo\\..\\bar")
    @settings(
        max_examples=200,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_safe_path_under_dir_never_escapes(self, filename, tmp_path):
        root = tmp_path / str(uuid.uuid4())
        root.mkdir()
        result = safe_path_under_dir(str(root), filename)
        if result is None:
            return
        root_resolved = os.path.realpath(str(root))
        resolved = os.path.realpath(result)
        assert resolved == root_resolved or resolved.startswith(root_resolved + os.sep)

    @given(filename=safe_segment())
    @settings(
        max_examples=50,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_safe_path_under_dir_accepts_safe_basenames(self, filename, tmp_path):
        root = tmp_path / str(uuid.uuid4())
        root.mkdir()
        # Create the file so the safe return value is a real on-disk path.
        (root / filename).write_text("x", encoding="utf-8")
        result = safe_path_under_dir(str(root), filename)
        assert result is not None
        assert os.path.isfile(result)
        assert os.path.basename(result) == filename


class TestResolvePathUnderDirOracle:
    @given(user_path=st.text())
    @example(user_path="")
    @example(user_path=".")
    @example(user_path="..")
    @example(user_path="../evil.txt")
    @example(user_path="/etc/passwd")
    @example(user_path="foo\\..\\bar")
    @example(user_path="foo\x00bar")
    @example(user_path="foo/../bar")
    @settings(
        max_examples=200,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_resolve_path_under_dir_never_escapes(self, user_path, tmp_path):
        root = tmp_path / str(uuid.uuid4())
        root.mkdir()
        result = resolve_path_under_dir(str(root), user_path)
        if result is None:
            return
        root_resolved = os.path.realpath(str(root))
        resolved = os.path.realpath(result)
        assert resolved == root_resolved or resolved.startswith(root_resolved + os.sep)

    @given(user_path=safe_relative_path())
    @settings(
        max_examples=50,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_resolve_path_under_dir_accepts_safe_subpaths(self, user_path, tmp_path):
        root = tmp_path / str(uuid.uuid4())
        root.mkdir()
        target = root / user_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("x", encoding="utf-8")
        result = resolve_path_under_dir(str(root), user_path)
        assert result is not None
        assert os.path.isfile(result)
        assert os.path.realpath(result) == os.path.realpath(str(target))


class TestNormalizeRelpathOracle:
    _TRAVERSAL: ClassVar[list[str]] = [
        "..",
        "../x",
        "..\\x",
        "a/../../b",
        "/etc/passwd",
        "/abs",
        "\\abs",
        "C:boot.ini",
        "C:/win",
        "//unc",
        "\\\\unc",
        "\x00",
        "a\x00b",
        "",
        ".",
    ]

    @given(path=st.text())
    @example(path="../x")
    @example(path="a/../b")
    @example(path="C:boot.ini")
    @settings(max_examples=300, deadline=None)
    def test_accepted_paths_are_relative_without_escape(self, path):
        try:
            cleaned = normalize_relpath(path)
        except PathJailError:
            return
        assert cleaned
        assert not os.path.isabs(cleaned)
        assert not cleaned.startswith(("/", "\\"))
        parts = cleaned.split("/")
        assert all(part not in ("", ".", "..") for part in parts)
        assert ".." not in parts

    @given(path=st.sampled_from(_TRAVERSAL))
    @settings(max_examples=50, deadline=None)
    def test_traversal_corpus_rejected(self, path):
        with pytest.raises(PathJailError):
            normalize_relpath(path)

    def test_strict_rejects_internal_dotdot(self):
        assert normalize_relpath("a/../b") == "b"
        with pytest.raises(PathJailError):
            normalize_relpath("a/../b", strict=True)

    def test_reserved_names_and_prefixes(self):
        with pytest.raises(PathJailError):
            normalize_relpath("a/.rns-filesync.db", reserved_names={".rns-filesync.db"})
        with pytest.raises(PathJailError):
            normalize_relpath(".rns-xfer-1/x", reserved_prefixes=(".rns-xfer-",))
        assert normalize_relpath("a/b.txt", reserved_names={"x"}) == "a/b.txt"

    def test_forbidden_part_predicate(self):
        with pytest.raises(PathJailError):
            normalize_relpath("a/.hidden/x", forbidden_part=lambda p: p.startswith("."))

    @pytest.mark.parametrize(
        "path",
        [
            "C:\\Windows\\system32",
            "C:..\\x",
            "\\\\server\\share\\f",
            "a\\b\\c.txt",
        ],
    )
    def test_windows_forms(self, path):
        if path == "a\\b\\c.txt":
            # Backslash is a separator on every platform by design.
            assert normalize_relpath(path) == "a/b/c.txt"
            return
        with pytest.raises(PathJailError):
            normalize_relpath(path)

    def test_reason_is_closed_set(self):
        for payload in [*self._TRAVERSAL, "ok.txt"]:
            try:
                normalize_relpath(payload)
            except PathJailError as exc:
                assert exc.reason in PathJailError.REASONS


class TestResolveUnderRootOracle:
    @given(user_path=st.text())
    @example(user_path="../evil.txt")
    @example(user_path="/etc/passwd")
    @example(user_path="a/b/c.txt")
    @settings(
        max_examples=200,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_accepted_never_leaves_root(self, user_path, tmp_path):
        root = tmp_path / str(uuid.uuid4())
        root.mkdir()
        try:
            resolved = resolve_under_root(str(root), user_path)
        except PathJailError:
            return
        root_resolved = os.path.realpath(str(root))
        resolved_real = os.path.realpath(resolved)
        assert resolved_real == root_resolved or resolved_real.startswith(
            root_resolved + os.sep
        )

    @pytest.mark.skipif(os.name == "nt", reason="symlink semantics differ")
    def test_symlink_out_rejected(self, tmp_path):
        root = tmp_path / "root"
        root.mkdir()
        outside = tmp_path / "outside"
        outside.mkdir()
        secret = outside / "secret.txt"
        secret.write_text("x", encoding="utf-8")
        (root / "link").symlink_to(secret)
        with pytest.raises(PathJailError):
            resolve_under_root(str(root), "link")
        # Symlinked parent dir pointing outside must also fail.
        (root / "dirlink").symlink_to(outside)
        with pytest.raises(PathJailError):
            resolve_under_root(str(root), "dirlink/secret.txt")

    @pytest.mark.skipif(os.name == "nt", reason="symlink semantics differ")
    def test_in_jail_symlink_allowed(self, tmp_path):
        root = tmp_path / "root"
        root.mkdir()
        target = root / "real.txt"
        target.write_text("x", encoding="utf-8")
        (root / "link").symlink_to(target)
        resolved = resolve_under_root(str(root), "link", must_exist=True)
        assert resolved == os.path.realpath(str(target))

    def test_must_exist_and_must_be_file(self, tmp_path):
        root = tmp_path / "root"
        root.mkdir()
        with pytest.raises(PathJailError) as excinfo:
            resolve_under_root(str(root), "missing", must_exist=True)
        assert excinfo.value.reason == "not_found"
        (root / "adir").mkdir()
        with pytest.raises(PathJailError) as excinfo:
            resolve_under_root(str(root), "adir", must_be_file=True)
        assert excinfo.value.reason == "not_found"
        assert resolve_under_root(str(root), "adir") == os.path.realpath(
            str(root / "adir")
        )

    def test_allow_root_semantics(self, tmp_path):
        root = tmp_path / "root"
        root.mkdir()
        root_real = os.path.realpath(str(root))
        assert resolve_under_root(str(root), None, allow_root=True) == root_real
        assert resolve_under_root(str(root), "", allow_root=True) == root_real
        with pytest.raises(PathJailError) as excinfo:
            resolve_under_root(str(root), "")
        assert excinfo.value.reason == "required"


class TestResolveUserPathOracle:
    @given(user_path=st.text())
    @example(user_path="../x")
    @example(user_path="~/x")
    @settings(
        max_examples=200,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_accepted_stays_under_allowed_roots(self, user_path, tmp_path):
        root = tmp_path / str(uuid.uuid4())
        root.mkdir()
        try:
            real = resolve_user_path(
                user_path,
                default_root=str(root),
                allowed_roots=(str(root),),
            )
        except PathJailError:
            return
        root_real = os.path.realpath(str(root))
        real_real = os.path.realpath(real)
        assert real_real == root_real or real_real.startswith(root_real + os.sep)

    def test_forbidden_names_rejected(self, tmp_path):
        root = tmp_path / "storage"
        (root / ".ssh").mkdir(parents=True)
        with pytest.raises(PathJailError) as excinfo:
            resolve_user_path(
                ".ssh/id",
                default_root=str(root),
                allowed_roots=(str(root),),
                forbidden_names={".ssh", ".gnupg"},
            )
        assert excinfo.value.reason == "forbidden"

    def test_no_roots_rejects(self, tmp_path):
        with pytest.raises(PathJailError):
            resolve_user_path("/tmp/x", allowed_roots=())

    def test_second_identity_bait(self, tmp_path):
        id_a = tmp_path / "id_a"
        id_b = tmp_path / "id_b"
        id_a.mkdir()
        id_b.mkdir()
        bait = id_b / "secret.txt"
        bait.write_text("x", encoding="utf-8")
        with pytest.raises(PathJailError):
            resolve_user_path(
                str(bait),
                default_root=str(id_a),
                allowed_roots=(str(id_a),),
            )
        assert bait.is_file()


class TestSafeBasenameOracle:
    @given(name=st.text())
    @example(name="a/b.txt")
    @example(name="a\\b.txt")
    @example(name="..")
    @example(name=".")
    @settings(max_examples=200, deadline=None)
    def test_accepted_is_plain_basename(self, name):
        base = safe_basename(name)
        if base is None:
            return
        assert base == os.path.basename(base.replace("\\", "/"))
        assert base not in (".", "..")
        assert "/" not in base and "\\" not in base and "\x00" not in base

    def test_forbidden_callable(self):
        assert safe_basename("identity", forbidden=lambda n: n == "identity") is None
        assert safe_basename("ok.txt", forbidden=lambda n: n == "identity") == "ok.txt"

    def test_non_str_rejected(self):
        assert safe_basename(None) is None
        assert safe_basename(123) is None


class TestIsSafeArchiveMember:
    @pytest.mark.parametrize(
        "name",
        [
            "a/b.txt",
            "dir/sub/file.md",
            "weird name.zip",
        ],
    )
    def test_accepts_normal_members(self, name):
        assert is_safe_archive_member(name)

    @pytest.mark.parametrize(
        "name",
        [
            "",
            ".",
            "..",
            "../x",
            "a/../b",
            "/abs",
            "a\\..\\b",
            "C:x",
            "a:b",
            "\x00",
            "a\x00b",
            None,
            5,
            # Windows hazards: device basenames and trailing dot/space aliases.
            "NUL",
            "nul.txt",
            "CON",
            "aux.ini",
            "PRN",
            "COM1",
            "com9.log",
            "LPT3",
            "dir/nul/x",
            "file.txt ",
            "file.txt.",
            "dir./x",
        ],
    )
    def test_rejects_unsafe_members(self, name):
        assert not is_safe_archive_member(name)


class TestRelativeToRootRoundTrip:
    @given(rel=safe_relative_path())
    @settings(
        max_examples=50,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_round_trip(self, rel, tmp_path):
        root = tmp_path / str(uuid.uuid4())
        root.mkdir()
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("x", encoding="utf-8")
        back = relative_to_root(str(root), str(target))
        assert back.replace("\\", "/") == rel
        resolved = resolve_under_root(str(root), back)
        assert resolved == os.path.realpath(str(target))

    def test_outside_rejected(self, tmp_path):
        root = tmp_path / "root"
        root.mkdir()
        outside = tmp_path / "outside"
        outside.mkdir()
        with pytest.raises(PathJailError):
            relative_to_root(str(root), str(outside))


class TestSmallHelpers:
    def test_is_under_root_requires_resolved(self):
        assert is_under_root("/a/b", "/a")
        assert is_under_root("/a", "/a")
        assert not is_under_root("/ab", "/a")
        assert not is_under_root("/a", "")
        assert not is_under_root("", "/a")

    def test_realpath_or_none_nul(self):
        assert realpath_or_none("a\x00b") is None
        assert realpath_or_none(None) is None
        assert realpath_or_none("") is None

    def test_is_direct_child(self, tmp_path):
        child = tmp_path / "child"
        child.write_text("x", encoding="utf-8")
        nested = tmp_path / "sub" / "deep"
        nested.parent.mkdir()
        nested.write_text("x", encoding="utf-8")
        assert is_direct_child(str(child), str(tmp_path))
        assert not is_direct_child(str(nested), str(tmp_path))
        assert not is_direct_child(str(tmp_path), str(tmp_path))

    def test_is_path_within_dir_nul(self):
        assert not is_path_within_dir("a\x00b", "/tmp")
        assert not is_path_within_dir("/tmp/x", "a\x00b")

    def test_is_under_root_prefix_boundary(self):
        # /rootx must not count as under /root.
        assert not is_under_root("/rootx/f", "/root")
        assert is_under_root("/root/f", "/root")

    def test_first_component_under(self):
        assert first_component_under("/a/b/c", "/a") == "b"
        assert first_component_under("/a", "/a") is None
        assert first_component_under("/x/b", "/a") is None


class TestVendorParity:
    """Central normalize_relpath must agree with the vendored filesync copy.

    The vendored module is an independent implementation, so this guards
    against the two drifting apart on vendor sync.
    """

    @given(path=st.text())
    @example(path=".rns-filesync.db")
    @example(path=".rns-xfer-abc")
    @example(path="a/b.txt")
    @settings(max_examples=300, deadline=None)
    def test_matches_vendored_normalize_relpath(self, path):
        from rns_filesync.paths import PathJailError as VendorPathJailError
        from rns_filesync.paths import normalize_relpath as vendor_normalize

        try:
            expected = vendor_normalize(path)
        except VendorPathJailError:
            expected = None
        try:
            actual = normalize_relpath(
                path,
                reserved_names={".rns-filesync.db"},
                reserved_prefixes=(".rns-xfer-",),
            )
        except PathJailError:
            actual = None
        assert actual == expected


class TestRequestClientIpOracle:
    class _Request:
        def __init__(self, remote, headers=None, scheme="http"):
            self.remote = remote
            self.headers = headers or {}
            self.scheme = scheme

    def _allowed(self, remote, _cidrs):
        return remote == "10.0.0.1"

    def test_client_ip_ignores_xff_when_not_trusted(self, monkeypatch):
        with monkeypatch.context() as m:
            m.setattr(
                "meshchatx.src.backend.ip_allowlist.client_ip_allowed", self._allowed
            )
            req = self._Request("203.0.113.4", {"X-Forwarded-For": "1.2.3.4"})
            assert request_client_ip(req, "10.0.0.0/8") == "203.0.113.4"

    def test_client_ip_uses_xff_when_trusted_and_present(self, monkeypatch):
        with monkeypatch.context() as m:
            m.setattr(
                "meshchatx.src.backend.ip_allowlist.client_ip_allowed", self._allowed
            )
            req = self._Request("10.0.0.1", {"X-Forwarded-For": "1.2.3.4, 5.6.7.8"})
            assert request_client_ip(req, "10.0.0.0/8") == "1.2.3.4"

    def test_client_ip_ignores_xff_when_cidrs_unset(self):
        req = self._Request("203.0.0.1", {"X-Forwarded-For": "1.2.3.4"})
        assert request_client_ip(req, None) == "203.0.0.1"
        assert request_client_ip(req, "") == "203.0.0.1"
