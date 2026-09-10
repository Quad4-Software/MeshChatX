# SPDX-License-Identifier: 0BSD

"""Property-based and adversarial oracles for meshchatx/src/path_utils.py."""

import os
import uuid

from hypothesis import HealthCheck, example, given, settings
from hypothesis import strategies as st

from meshchatx.src.path_utils import (
    is_path_within_dir,
    request_client_ip,
    resolve_path_under_dir,
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
