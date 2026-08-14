# SPDX-License-Identifier: 0BSD

from unittest.mock import MagicMock, patch

import pytest
import RNS

from meshchatx.src.backend.nomadnet_downloader import (
    NomadnetDownloader,
    NomadnetFileDownloader,
    NomadnetPageDownloader,
    _nomadnet_links_lock,
    get_cached_active_link,
    nomadnet_cached_links,
)


@pytest.fixture(autouse=True)
def clear_nomadnet_link_cache():
    with _nomadnet_links_lock:
        nomadnet_cached_links.clear()
        from meshchatx.src.backend.nomadnet_downloader import _nomadnet_link_last_used

        _nomadnet_link_last_used.clear()
    yield
    with _nomadnet_links_lock:
        nomadnet_cached_links.clear()
        from meshchatx.src.backend.nomadnet_downloader import _nomadnet_link_last_used

        _nomadnet_link_last_used.clear()


@pytest.fixture
def downloader():
    return NomadnetDownloader(
        b"dest",
        "/path",
        "data",
        MagicMock(),
        MagicMock(),
        MagicMock(),
    )


def test_cancel_sets_flag_and_cancels_resource():
    on_failure = MagicMock()
    d = NomadnetDownloader(b"123", "/test", None, MagicMock(), on_failure, MagicMock())
    d.request_receipt = MagicMock()
    d.request_receipt.resource = MagicMock()
    d.cancel()
    assert d.is_cancelled is True
    d.request_receipt.resource.cancel.assert_called_once()


def test_cancel_removes_link_from_cache():
    mock_link = MagicMock()
    mock_link.status = RNS.Link.ACTIVE
    with _nomadnet_links_lock:
        nomadnet_cached_links[b"x"] = mock_link

    on_failure = MagicMock()
    d = NomadnetDownloader(b"x", "/p", None, MagicMock(), on_failure, MagicMock())
    d.link = mock_link
    d.cancel()

    assert get_cached_active_link(b"x") is None
    mock_link.teardown.assert_called_once()


def test_get_cached_active_link_evicts_stale():
    dead = MagicMock()
    dead.status = None
    with _nomadnet_links_lock:
        nomadnet_cached_links[b"z"] = dead

    assert get_cached_active_link(b"z") is None
    with _nomadnet_links_lock:
        assert b"z" not in nomadnet_cached_links


@pytest.mark.asyncio
async def test_download_no_path(downloader):
    with (
        patch.object(RNS.Transport, "has_path", return_value=False),
        patch.object(RNS.Transport, "request_path"),
    ):
        await downloader.download(path_lookup_timeout=0.1)
        downloader._download_failure_callback.assert_called_with(
            "Could not find path to destination.",
        )


@pytest.mark.asyncio
async def test_download_cached_link(downloader):
    mock_link = MagicMock()
    mock_link.status = RNS.Link.ACTIVE
    with _nomadnet_links_lock:
        nomadnet_cached_links[b"dest"] = mock_link

    with patch.object(downloader, "link_established") as mock_established:
        await downloader.download()
        mock_established.assert_called_with(mock_link)


def test_page_downloader_invalid_utf8_replaced():
    on_ok = MagicMock()
    on_fail = MagicMock()
    pd = NomadnetPageDownloader(
        b"ab" * 8,
        "/page.mu",
        None,
        on_ok,
        on_fail,
        MagicMock(),
    )
    rr = MagicMock()
    rr.response = b"hello\xff\xfeinvalid"
    pd.on_download_success(rr)
    on_ok.assert_called_once()
    assert "\ufffd" in on_ok.call_args[0][0]
    on_fail.assert_not_called()


def test_page_downloader_empty_response():
    on_ok = MagicMock()
    on_fail = MagicMock()
    pd = NomadnetPageDownloader(
        b"ab" * 8,
        "/page.mu",
        None,
        on_ok,
        on_fail,
        MagicMock(),
    )
    rr = MagicMock()
    rr.response = None
    pd.on_download_success(rr)
    on_fail.assert_called_once_with("empty_response")
    on_ok.assert_not_called()


def test_file_downloader_list_response_short_list_no_crash():
    on_ok = MagicMock()
    on_fail = MagicMock()
    fd = NomadnetFileDownloader(
        b"ab" * 8,
        "/f.bin",
        on_ok,
        on_fail,
        MagicMock(),
    )
    rr = MagicMock()
    rr.response = [b"only"]
    fd.on_download_success(rr)
    on_fail.assert_called_once_with("unsupported_response")


def test_file_downloader_passes_query_data_to_parent():
    fd = NomadnetFileDownloader(
        b"ab" * 8,
        "/file/data.bin",
        MagicMock(),
        MagicMock(),
        MagicMock(),
        data="foo=bar",
    )
    assert fd.data == "foo=bar"


def test_nomad_link_cache_evicts_over_cap():
    from meshchatx.src.backend import nomadnet_downloader as nd

    original_max = nd.MAX_CACHED_LINKS
    nd.MAX_CACHED_LINKS = 2
    try:
        links = []
        for i in range(3):
            link = MagicMock()
            link.status = RNS.Link.ACTIVE
            dest = bytes([i]) * 16
            nd._cache_link_if_active(dest, link)
            links.append((dest, link))
        assert nd.cached_link_count() == 2
        assert get_cached_active_link(links[0][0]) is None
        links[0][1].teardown.assert_called()
        assert get_cached_active_link(links[1][0]) is links[1][1]
        assert get_cached_active_link(links[2][0]) is links[2][1]
    finally:
        nd.MAX_CACHED_LINKS = original_max


def test_clear_all_nomadnet_cached_links_tears_down_active():
    from meshchatx.src.backend.nomadnet_downloader import (
        clear_all_nomadnet_cached_links,
    )

    link = MagicMock()
    link.status = RNS.Link.ACTIVE
    with _nomadnet_links_lock:
        nomadnet_cached_links[b"x" * 16] = link
    assert clear_all_nomadnet_cached_links() == 1
    assert get_cached_active_link(b"x" * 16) is None
    link.teardown.assert_called_once()


def test_file_downloader_sanitizes_fallback_name():
    on_ok = MagicMock()
    on_fail = MagicMock()
    fd = NomadnetFileDownloader(
        b"ab" * 8,
        "/f.bin",
        on_ok,
        on_fail,
        MagicMock(),
    )
    rr = MagicMock()
    rr.response = ["../../etc/passwd", b"ok"]
    fd.on_download_success(rr)
    on_ok.assert_called_once_with("passwd", b"ok")
    on_fail.assert_not_called()
