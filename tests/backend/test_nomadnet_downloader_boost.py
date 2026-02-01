import pytest
from unittest.mock import MagicMock, patch
from meshchatx.src.backend.nomadnet_downloader import NomadnetDownloader
import RNS


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
    from meshchatx.src.backend.nomadnet_downloader import nomadnet_cached_links

    nomadnet_cached_links[b"dest"] = mock_link

    with patch.object(downloader, "link_established") as mock_established:
        await downloader.download()
        mock_established.assert_called_with(mock_link)

    del nomadnet_cached_links[b"dest"]
