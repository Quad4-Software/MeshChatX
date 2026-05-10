# SPDX-License-Identifier: 0BSD

"""Regression: Nomad net downloads must emit websocket ``started`` before scheduling ``download()``."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

import meshchatx.meshchat as meshchat_module


@pytest.mark.asyncio
async def test_nomadnet_page_download_started_before_download_async_scheduled(
    mock_app, monkeypatch
):
    mock_app._try_serve_local_page_node = MagicMock(return_value=None)

    events = []
    mock_ws = MagicMock()
    mock_ws.send_str = AsyncMock(
        side_effect=lambda payload: events.append(("send_str", json.loads(payload)))
    )

    inner_async_utils = meshchat_module.AsyncUtils
    prev_run_async = inner_async_utils.run_async

    def wrapping_run_async(coro):
        events.append(("run_async", coro))
        return prev_run_async(coro)

    monkeypatch.setattr(inner_async_utils, "run_async", wrapping_run_async)

    dh = "a" * 32
    await mock_app.on_websocket_data_received(
        mock_ws,
        {
            "type": "nomadnet.page.download",
            "nomadnet_page_download": {
                "destination_hash": dh,
                "page_path": "/page/index.mu",
                "field_data": None,
            },
        },
    )

    assert len(events) >= 2
    assert events[0][0] == "send_str"
    assert events[0][1]["type"] == "nomadnet.page.download"
    assert events[0][1]["nomadnet_page_download"]["status"] == "started"
    assert events[1][0] == "run_async"


@pytest.mark.asyncio
async def test_nomadnet_file_download_started_before_download_async_scheduled(
    mock_app, monkeypatch
):
    mock_app._try_serve_local_page_node_file = MagicMock(return_value=None)

    events = []
    mock_ws = MagicMock()
    mock_ws.send_str = AsyncMock(
        side_effect=lambda payload: events.append(("send_str", json.loads(payload)))
    )

    inner_async_utils = meshchat_module.AsyncUtils
    prev_run_async = inner_async_utils.run_async

    def wrapping_run_async(coro):
        events.append(("run_async", coro))
        return prev_run_async(coro)

    monkeypatch.setattr(inner_async_utils, "run_async", wrapping_run_async)

    dh = "b" * 32
    await mock_app.on_websocket_data_received(
        mock_ws,
        {
            "type": "nomadnet.file.download",
            "nomadnet_file_download": {
                "destination_hash": dh,
                "file_path": "/files/readme.txt",
            },
        },
    )

    assert len(events) >= 2
    assert events[0][0] == "send_str"
    assert events[0][1]["type"] == "nomadnet.file.download"
    assert events[0][1]["nomadnet_file_download"]["status"] == "started"
    assert events[1][0] == "run_async"


@pytest.mark.asyncio
async def test_nomadnet_file_download_with_data_passed_to_downloader(
    mock_app, monkeypatch
):
    """Query-param data from the WS payload must reach NomadnetFileDownloader."""
    mock_app._try_serve_local_page_node_file = MagicMock(return_value=None)

    from meshchatx.src.backend import nomadnet_downloader

    captured = {}
    orig_init = nomadnet_downloader.NomadnetFileDownloader.__init__

    def capturing_init(self, *args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        # Don't call real init to avoid RNS side-effects
        self.is_cancelled = False
        self.destination_hash = args[0]
        self.path = args[1]
        self.data = kwargs.get("data")

    monkeypatch.setattr(
        nomadnet_downloader.NomadnetFileDownloader, "__init__", capturing_init
    )

    mock_ws = MagicMock()
    mock_ws.send_str = AsyncMock()

    dh = "c" * 32
    await mock_app.on_websocket_data_received(
        mock_ws,
        {
            "type": "nomadnet.file.download",
            "nomadnet_file_download": {
                "destination_hash": dh,
                "file_path": "/files/report.pdf",
                "data": "version=2&format=raw",
            },
        },
    )

    assert captured["kwargs"].get("data") == {"var_version": "2&format=raw"}
    assert captured["args"][0] == bytes.fromhex(dh)
    assert captured["args"][1] == "/files/report.pdf"

    monkeypatch.setattr(
        nomadnet_downloader.NomadnetFileDownloader, "__init__", orig_init
    )
