# SPDX-License-Identifier: 0BSD
"""Oracle tests for MeshChatX local page-node image file grants."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from meshchatx.meshchat import ReticulumMeshChat


@pytest.fixture
def mock_app():
    app = ReticulumMeshChat.__new__(ReticulumMeshChat)
    app._page_file_grants = {}
    return app


def _webp_bytes() -> bytes:
    return (
        b"RIFF"
        + (20).to_bytes(4, "little")
        + b"WEBP"
        + b"VP8 "
        + (12).to_bytes(4, "little")
        + b"\x00" * 8
    )


def test_extract_page_file_links_finds_relative_and_absolute_webp():
    app = ReticulumMeshChat.__new__(ReticulumMeshChat)
    content = (
        "`[A`:/file/photo.webp`img=1] and "
        "`[B`f64a846313b874ee4a357040807f8c77:/file/diagram.webp`img=1] and "
        "`[C`:/file/../etc/shadow.webp`img=1]"
    )
    links = app._extract_page_file_links(content)
    assert "photo.webp" in links
    assert "diagram.webp" in links
    assert "../etc/shadow.webp" not in links


def test_page_file_grant_blocks_unreferenced_file(mock_app):
    client = MagicMock()
    dest = bytes.fromhex("f64a846313b874ee4a357040807f8c77")
    page = "/page/index.mu"
    page_content = "`[A`:/file/photo.webp`img=1]"

    mock_app._register_page_file_grant(client, dest, page, page_content)
    assert mock_app._check_page_file_grant(client, dest, page, "/file/photo.webp")
    assert not mock_app._check_page_file_grant(client, dest, page, "/file/other.webp")


def test_page_file_grant_expires(mock_app):
    client = MagicMock()
    dest = bytes.fromhex("f64a846313b874ee4a357040807f8c77")
    page = "/page/index.mu"
    page_content = "`[A`:/file/photo.webp`img=1]"

    with patch("time.time", return_value=0):
        mock_app._register_page_file_grant(client, dest, page, page_content, ttl=5)
    with patch("time.time", return_value=10):
        assert not mock_app._check_page_file_grant(
            client, dest, page, "/file/photo.webp"
        )


def test_try_serve_local_page_node_file_requires_grant_for_images():
    app = ReticulumMeshChat.__new__(ReticulumMeshChat)
    app._page_file_grants = {}

    fake_node = MagicMock()
    fake_node.running = True
    fake_node.destination.hash = bytes.fromhex("f64a846313b874ee4a357040807f8c77")
    fake_node.read_hosted_file.return_value = ("test.webp", _webp_bytes())

    app.page_node_manager = MagicMock()
    app.page_node_manager.nodes = {"test": fake_node}

    client = MagicMock()
    dest = bytes.fromhex("f64a846313b874ee4a357040807f8c77")

    # Image requests without a page grant are refused.
    result = app._try_serve_local_page_node_file(
        dest,
        "/file/test.webp",
        client=client,
        page_path="/page/index.mu",
        request_data={"image_id": 0},
    )
    assert result is None

    # After registering the page grant the same image can be served.
    app._register_page_file_grant(
        client, dest, "/page/index.mu", "`[A`:/file/test.webp`img=1]"
    )
    result = app._try_serve_local_page_node_file(
        dest,
        "/file/test.webp",
        client=client,
        page_path="/page/index.mu",
        request_data={"image_id": 0},
    )
    assert result == ("test.webp", _webp_bytes())
