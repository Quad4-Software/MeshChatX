"""
Path traversal regression tests and property-based fuzzing for mesh PageNode
page/file APIs and normalize_page_filename.
"""

import os
import shutil
import tempfile
from unittest.mock import MagicMock, patch

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from meshchatx.src.backend.page_node import (
    PageNode,
    _safe_mesh_file_basename,
    normalize_page_filename,
)


@pytest.fixture
def node_dir():
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def mock_rns():
    with patch("meshchatx.src.backend.page_node.RNS") as mock:
        mock_identity = MagicMock()
        mock_identity.hash = b"\x01" * 16
        mock_identity.get_public_key.return_value = b"\x02" * 64

        mock_destination = MagicMock()
        mock_destination.hash = b"\x03" * 16

        mock.Identity.return_value = mock_identity
        mock.Identity.from_file.return_value = mock_identity
        mock.Destination.return_value = mock_destination
        mock.Destination.IN = 1
        mock.Destination.SINGLE = 0
        mock.Destination.ALLOW_ALL = 0xFF
        mock.Transport = MagicMock()

        yield mock, mock_identity, mock_destination


def _make_node(node_dir, mock_rns):
    _, mock_identity, _ = mock_rns
    return PageNode(
        node_id="sec-test-node",
        name="Sec Test",
        base_dir=node_dir,
        identity=mock_identity,
    )


TRAVERSAL_PAGE_INPUTS = [
    "../../etc/passwd",
    "..\\..\\windows\\system32",
    "page/../../../secret.mu",
    "/page/../../../x.mu",
    "foo/../bar/../baz.mu",
    "....//....//evil.mu",
    "\0../x.mu",
]


class TestPathTraversalKnownVectors:
    def test_normalize_strips_to_basename(self):
        for raw in TRAVERSAL_PAGE_INPUTS:
            try:
                out = normalize_page_filename(raw)
            except ValueError:
                continue
            assert os.sep not in out
            assert "/" not in out
            assert "\\" not in out
            assert out not in (".", "..")
            assert os.path.basename(out) == out

    def test_add_page_never_writes_outside_pages_dir(self, node_dir, mock_rns):
        node = _make_node(node_dir, mock_rns)
        node.setup()
        for raw in TRAVERSAL_PAGE_INPUTS:
            try:
                saved = node.add_page(raw, "probe")
            except ValueError:
                continue
            full = os.path.realpath(os.path.join(node.pages_dir, saved))
            root = os.path.realpath(node.pages_dir)
            assert full == root or full.startswith(root + os.sep), (raw, saved, full)

    def test_add_file_rejects_dot_segments(self, node_dir, mock_rns):
        node = _make_node(node_dir, mock_rns)
        node.setup()
        with pytest.raises(ValueError):
            node.add_file("..", b"x")
        with pytest.raises(ValueError):
            node.add_file(".", b"x")
        with pytest.raises(ValueError):
            node.add_file("  ..  ", b"x")

    def test_remove_file_dot_segments_returns_false(self, node_dir, mock_rns):
        node = _make_node(node_dir, mock_rns)
        node.setup()
        assert node.remove_file("..") is False
        assert node.remove_file(".") is False

    def test_safe_mesh_file_basename(self):
        assert _safe_mesh_file_basename("a/b/c.txt") == "c.txt"
        with pytest.raises(ValueError):
            _safe_mesh_file_basename("..")
        with pytest.raises(ValueError):
            _safe_mesh_file_basename("")


@settings(max_examples=300, deadline=None)
@given(name=st.text(min_size=0, max_size=500))
def test_normalize_page_filename_never_emits_path_segments(name):
    try:
        out = normalize_page_filename(name)
    except ValueError:
        return
    assert os.sep not in out
    assert "/" not in out
    assert "\\" not in out
    assert out not in (".", "..")


@settings(
    max_examples=200,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(name=st.text(min_size=0, max_size=500))
def test_add_page_writes_only_under_pages_dir(mock_rns, name):
    with tempfile.TemporaryDirectory() as node_dir:
        node = _make_node(node_dir, mock_rns)
        node.setup()
        try:
            saved = node.add_page(name, "x")
        except ValueError:
            return
        full = os.path.realpath(os.path.join(node.pages_dir, saved))
        root = os.path.realpath(node.pages_dir)
        assert full == root or full.startswith(root + os.sep)


@settings(
    max_examples=200,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(fname=st.text(min_size=0, max_size=500))
def test_add_file_writes_only_under_files_dir(mock_rns, fname):
    with tempfile.TemporaryDirectory() as node_dir:
        node = _make_node(node_dir, mock_rns)
        node.setup()
        try:
            saved = node.add_file(fname, b"x")
        except ValueError:
            return
        full = os.path.realpath(os.path.join(node.files_dir, saved))
        root = os.path.realpath(node.files_dir)
        assert full == root or full.startswith(root + os.sep)


class TestPageRespondersTraversal:
    def test_page_responder_ignores_path_in_request_path(self, node_dir, mock_rns):
        node = _make_node(node_dir, mock_rns)
        node.setup()
        node.add_page("safe.mu", "ok")
        responder = node._make_page_responder("safe.mu")
        result = responder("/page/../../../etc/passwd", None, "r", "l", None, 0)
        assert result == b"ok"

    def test_file_responder_ignores_path_prefix_in_request_path(
        self, node_dir, mock_rns
    ):
        node = _make_node(node_dir, mock_rns)
        node.setup()
        node.add_file("blob.bin", b"data")
        responder = node._make_file_responder("blob.bin")
        out = responder("/file/../blob.bin", None, "r", "l", None, 0)
        assert isinstance(out, list)
        out[0].close()


def test_try_serve_local_helpers_strip_traversal():
    """Regression: meshchat local serve must not join parent dirs for file names."""
    from meshchatx.meshchat import ReticulumMeshChat

    app = MagicMock(spec=ReticulumMeshChat)
    node = MagicMock()
    node.running = True
    node.destination = MagicMock()
    node.destination.hash = b"\xab" * 16
    node.files_dir = "/tmp/mesh_files"
    node.pages_dir = "/tmp/mesh_pages"
    node._stats = {"files_served": 0, "pages_served": 0}
    node.get_page_content = MagicMock(return_value="page ok")
    app.page_node_manager = MagicMock()
    app.page_node_manager.nodes = {"1": node}

    dh = node.destination.hash
    file_out = ReticulumMeshChat._try_serve_local_page_node_file(
        app,
        dh,
        "/file/../..",
    )
    assert file_out is None

    page_out = ReticulumMeshChat._try_serve_local_page_node(
        app,
        dh,
        "/page/../../../x.mu",
    )
    node.get_page_content.assert_called_once()
    called = node.get_page_content.call_args[0][0]
    assert called == "x.mu"
    assert page_out == "page ok"
