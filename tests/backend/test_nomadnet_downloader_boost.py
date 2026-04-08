import threading

import pytest
import RNS
from unittest.mock import MagicMock, patch

from meshchatx.src.backend.nomadnet_downloader import (
    NomadnetDownloader,
    NomadnetFileDownloader,
    NomadnetPageDownloader,
    get_cached_active_link,
    nomadnet_cached_links,
    _nomadnet_links_lock,
)


@pytest.fixture(autouse=True)
def clear_nomadnet_link_cache():
    with _nomadnet_links_lock:
        nomadnet_cached_links.clear()
    yield
    with _nomadnet_links_lock:
        nomadnet_cached_links.clear()


@pytest.fixture
def downloader():
    on_success = MagicMock()
    on_failure = MagicMock()
    on_progress = MagicMock()
    return NomadnetDownloader(
        b"dest", "/path", "data", on_success, on_failure, on_progress
    )


def test_downloader_init(downloader):
    assert downloader.destination_hash == b"dest"
    assert downloader.path == "/path"
    assert downloader.is_cancelled is False


def test_downloader_cancel(downloader):
    downloader.cancel()
    assert downloader.is_cancelled is True
    downloader._download_failure_callback.assert_called_with("cancelled")


def test_cancel_removes_link_from_cache():
    mock_link = MagicMock()
    mock_link.status = RNS.Link.ACTIVE
    with _nomadnet_links_lock:
        nomadnet_cached_links[b"x"] = mock_link

    on_success = MagicMock()
    on_failure = MagicMock()
    on_progress = MagicMock()
    d = NomadnetDownloader(b"x", "/p", None, on_success, on_failure, on_progress)
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
            "Could not find path to destination."
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


@pytest.mark.asyncio
async def test_download_uses_path_wait_cache_hit(downloader):
    """Another task may populate the cache while we wait for a path."""
    mock_link = MagicMock()
    mock_link.status = RNS.Link.ACTIVE

    call_count = {"n": 0}

    def has_path_side_effect(dest):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return False
        if call_count["n"] == 2:
            with _nomadnet_links_lock:
                nomadnet_cached_links[dest] = mock_link
        return True

    with (
        patch.object(RNS.Transport, "has_path", side_effect=has_path_side_effect),
        patch.object(RNS.Transport, "request_path"),
    ):
        with patch.object(downloader, "link_established") as mock_established:
            await downloader.download(
                path_lookup_timeout=5, link_establishment_timeout=5
            )

    mock_established.assert_called_once_with(mock_link)


def test_page_downloader_invalid_utf8_replaced():
    on_ok = MagicMock()
    on_fail = MagicMock()
    on_progress = MagicMock()
    pd = NomadnetPageDownloader(
        b"ab" * 8,
        "/page.mu",
        None,
        on_ok,
        on_fail,
        on_progress,
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


def test_cache_lock_serializes_mutations():
    mock_link = MagicMock()
    mock_link.status = RNS.Link.ACTIVE
    errors = []

    def worker():
        try:
            with _nomadnet_links_lock:
                nomadnet_cached_links[b"t"] = mock_link
                assert nomadnet_cached_links[b"t"] is mock_link
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors
