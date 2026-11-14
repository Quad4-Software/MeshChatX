# SPDX-License-Identifier: 0BSD
"""Bug-hunt tests: WS dispatch/handlers and HTTP route audit.

Each test asserts the SECURE behaviour. A failure demonstrates a real bug.
"""

import asyncio
import json
import secrets
import sys
import threading
import time
import types
from asyncio.threads import to_thread as _real_to_thread
from threading import Thread as _RealThread
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp import FormData, web
from aiohttp.test_utils import TestClient, TestServer
from aiohttp_session import setup as setup_session

from meshchatx.src.backend.http.ws.handlers_lxmf import handle_lxm_ingest_uri
from meshchatx.src.backend.http.ws.handlers_nomad import (
    handle_nomadnet_download_cancel,
)
from tests.backend.conftest import (
    extend_meshchat_middlewares,
    fetch_api_csrf_headers,
)
from tests.backend.demo_http_support import build_test_aio_app


def _ws_broadcast_stubs(app):
    app.send_config_to_websocket_clients = AsyncMock()
    app.send_active_sessions_to_websocket_clients = AsyncMock()


def _enable_real_to_thread(monkeypatch):
    """mock_app patches asyncio.to_thread to run synchronously and mocks threading.Thread, which makes to_thread-based handlers indistinguishable from blocking ones. Restore both so non-blocking behavior is exercised."""
    monkeypatch.setattr(threading, "Thread", _RealThread)

    monkeypatch.setattr(asyncio, "to_thread", _real_to_thread)


# ---------------------------------------------------------------------------
# 1. nomadnet.download.cancel has no per-client ownership check (IDOR)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_nomad_download_cancel_does_not_verify_client_ownership(mock_app):
    """download_id is a global sequential counter; any WS client can cancel another client's in-flight download because the handler never compares downloader._meshchatx_client to the requesting client."""
    victim_client = MagicMock()

    attacker_client = MagicMock()
    attacker_client.send_str = AsyncMock()

    downloader = MagicMock()
    downloader._meshchatx_client = victim_client
    mock_app.active_downloads[4242] = downloader

    await handle_nomadnet_download_cancel(
        mock_app,
        attacker_client,
        {"download_id": 4242},
    )

    # Secure behaviour: a download owned by a different client must survive.
    assert mock_app.active_downloads.get(4242) is downloader
    downloader.cancel.assert_not_called()


# ---------------------------------------------------------------------------
# 2. lxm.ingest_uri runs the synchronous LXMF decode on the event loop
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_lxm_ingest_uri_does_not_block_event_loop():
    """handle_lxm_ingest_uri calls app.message_router.ingest_lxm_uri (base64 decode + LXMF parse/decrypt of up to ~9 MiB) synchronously. A concurrent coroutine must still get loop time while ingest runs."""

    def slow_ingest(uri, **_kwargs):
        time.sleep(0.5)
        return False

    # Stub app: the mock_app fixture patches asyncio.to_thread to run
    # synchronously (threading.Thread is mocked there), which would make a
    # non-blocking handler indistinguishable from a blocking one.
    app = MagicMock()
    app.message_router.ingest_lxm_uri = slow_ingest

    client = MagicMock()
    client.send_str = AsyncMock()

    probe_ran = asyncio.Event()

    async def probe():
        await asyncio.sleep(0.05)
        probe_ran.set()

    probe_task = asyncio.create_task(probe())
    await handle_lxm_ingest_uri(app, client, {"uri": "lxmf://QUJD"})

    # The probe only needed 50 ms of loop time; a non-blocking handler would
    # have let it finish during the (simulated) 500 ms ingest.
    assert probe_ran.is_set(), "event loop was blocked by synchronous ingest"
    await probe_task


# ---------------------------------------------------------------------------
# 3. lxm.generate_paper_uri has no payload size cap (envelope gap)
# ---------------------------------------------------------------------------


def test_generate_paper_uri_content_is_size_capped():
    """lxm.ingest_uri caps uri at WS_PAPER_URI_MAX_CHARS but the symmetric lxm.generate_paper_uri content field is unchecked, so a ~50 MiB frame can drive LXMF encrypt + base64 on the event loop."""
    from meshchatx.src.backend.http.ws.dispatch import _KNOWN_TYPES
    from meshchatx.src.backend.websocket_runtime import (
        WS_PAPER_URI_MAX_CHARS,
        validate_ws_envelope,
    )

    oversized = "x" * (WS_PAPER_URI_MAX_CHARS + 1)
    _t, err = validate_ws_envelope(
        {
            "type": "lxm.generate_paper_uri",
            "destination_hash": "ab" * 16,
            "content": oversized,
        },
        _KNOWN_TYPES,
    )
    assert err == "payload_too_large"

    # Control: the ingest side of the same feature IS capped.
    _t2, err2 = validate_ws_envelope(
        {"type": "lxm.ingest_uri", "uri": oversized},
        _KNOWN_TYPES,
    )
    assert err2 == "payload_too_large"


# ---------------------------------------------------------------------------
# 4. Binary msgpack frames pay flat rate cost 1.0 for heavy mutators
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.usefixtures("require_loopback_tcp")
async def test_binary_ws_frames_bypass_heavy_mutator_rate_cost(
    mock_app,
    monkeypatch,
):
    """TEXT lxm.generate_paper_uri costs WS_RATE_COST_HEAVY (5) tokens; the BINARY branch of the /ws loop always charges 1.0 regardless of the decoded type, giving heavy mutators a ~5x rate discount."""
    fake_msgpack = types.SimpleNamespace(
        unpackb=lambda data, raw=False: json.loads(data),
    )
    monkeypatch.setitem(sys.modules, "msgpack", fake_msgpack)

    _ws_broadcast_stubs(mock_app)

    accepted_binary = []
    orig_binary = mock_app.on_websocket_binary_received

    async def binary_spy(client, data):
        accepted_binary.append(data)
        await orig_binary(client, data)

    mock_app.on_websocket_binary_received = binary_spy

    aio_app = build_test_aio_app(mock_app)
    async with TestClient(TestServer(aio_app)) as client:
        ws = await client.ws_connect("/ws")
        # Enable the binary rns.link capability (runtime control, cost 1).
        await ws.send_str(
            json.dumps({"type": "ws.caps", "binary_rns_link": True}),
        )
        await ws.receive()  # caps ack

        # 15 heavy mutators as msgpack binary frames. Bucket burst is 60;
        # at the correct cost of 5 only ~11 could pass. At the buggy flat
        # cost of 1.0 all 15 pass.
        payload = {
            "type": "lxm.generate_paper_uri",
            "destination_hash": "ab" * 16,
            "content": "hi",
        }
        frame = json.dumps(payload).encode()
        for _ in range(15):
            await ws.send_bytes(frame)
        await asyncio.sleep(0.6)
        await ws.close()

    assert len(accepted_binary) <= 11, (
        f"{len(accepted_binary)} heavy mutators accepted via binary frames; "
        "expected <=11 at the same 5-token cost as text frames"
    )


# ---------------------------------------------------------------------------
# 5. HTTP routes that run sync work on the event loop
# ---------------------------------------------------------------------------


async def _status_latency_during(client, trigger):
    """Fire *trigger* (a request coroutine factory) and time a concurrent GET /api/v1/status. The poll timestamp is taken at task creation so loop stalls queueing the request count against the latency. Returns (latency_seconds, trigger_response)."""
    latency = {}

    poll_created = time.monotonic()

    async def poll():
        resp = await client.get("/api/v1/status")
        latency["dt"] = time.monotonic() - poll_created
        latency["status"] = resp.status

    trigger_task = asyncio.create_task(trigger())
    # Give the trigger time to reach its blocking call.
    await asyncio.sleep(0.1)
    poll_task = asyncio.create_task(poll())
    trigger_resp = await trigger_task
    await poll_task
    return latency["dt"], trigger_resp


@pytest.mark.asyncio
@pytest.mark.usefixtures("require_loopback_tcp")
async def test_translation_pack_import_does_not_block_event_loop(
    mock_app,
    monkeypatch,
):
    """import_translation_pack calls translation_pack_manager.import_archive (zip extraction of up to 512 MiB) synchronously instead of asyncio.to_thread."""
    _enable_real_to_thread(monkeypatch)

    manager = mock_app.translation_pack_manager

    def slow_import(_path):
        time.sleep(0.6)
        return []

    monkeypatch.setattr(manager, "import_archive", slow_import)

    aio_app = build_test_aio_app(mock_app)
    async with TestClient(TestServer(aio_app)) as client:
        headers = await fetch_api_csrf_headers(client)

        form = FormData()
        form.add_field(
            "file",
            b"not-a-real-zip",
            filename="pack.zip",
            content_type="application/zip",
        )

        async def trigger():
            return await client.post(
                "/api/v1/translation/packs/import",
                headers=headers,
                data=form,
            )

        dt, resp = await _status_latency_during(client, trigger)
        assert resp.status == 200
        assert dt < 0.4, (
            f"GET /status took {dt:.2f}s while import ran; "
            "event loop was blocked by synchronous import_archive"
        )


@pytest.mark.asyncio
@pytest.mark.usefixtures("require_loopback_tcp")
async def test_maintenance_clear_announces_does_not_block_event_loop(
    mock_app,
    monkeypatch,
):
    """DELETE /maintenance/announces runs delete_all_announces on the event loop while sibling maintenance handlers use asyncio.to_thread."""
    _enable_real_to_thread(monkeypatch)

    dao = mock_app.database.announces
    orig = dao.delete_all_announces

    def slow_delete(*args, **kwargs):
        time.sleep(0.6)
        return orig(*args, **kwargs)

    monkeypatch.setattr(dao, "delete_all_announces", slow_delete)

    aio_app = build_test_aio_app(mock_app)
    async with TestClient(TestServer(aio_app)) as client:
        headers = await fetch_api_csrf_headers(client)

        async def trigger():
            return await client.delete(
                "/api/v1/maintenance/announces",
                headers=headers,
            )

        dt, resp = await _status_latency_during(client, trigger)
        assert resp.status == 200
        assert dt < 0.4, (
            f"GET /status took {dt:.2f}s while delete ran; "
            "event loop was blocked by synchronous DB call"
        )


@pytest.mark.asyncio
@pytest.mark.usefixtures("require_loopback_tcp")
async def test_page_node_file_upload_does_not_block_event_loop(
    mock_app,
    monkeypatch,
):
    """page_nodes_upload_file calls node.add_file -> atomic_write_bytes (up to 64 MiB write + fsync) synchronously on the event loop."""
    _enable_real_to_thread(monkeypatch)

    node = mock_app.page_node_manager.create_node("hunt-node")
    node_id = node.get_status()["node_id"]

    def slow_add_file(name, data):
        time.sleep(0.6)
        return name

    monkeypatch.setattr(node, "add_file", slow_add_file)

    aio_app = build_test_aio_app(mock_app)
    async with TestClient(TestServer(aio_app)) as client:
        headers = await fetch_api_csrf_headers(client)

        form = FormData()
        form.add_field(
            "file",
            b"x" * 4096,
            filename="blob.bin",
            content_type="application/octet-stream",
        )

        async def trigger():
            return await client.post(
                f"/api/v1/page-nodes/{node_id}/files",
                headers=headers,
                data=form,
            )

        dt, resp = await _status_latency_during(client, trigger)
        assert resp.status == 200
        assert dt < 0.4, (
            f"GET /status took {dt:.2f}s while file write ran; "
            "event loop was blocked by synchronous file write"
        )


# ---------------------------------------------------------------------------
# 6. translation pack fetch reads request.json() with no app-level cap
# ---------------------------------------------------------------------------


def _build_aio_app_with_client_max(app, max_size):
    app.session_secret_key = secrets.token_urlsafe(32)
    app.listen_host = "127.0.0.1"
    app.listen_port = 8000
    app.use_https = False
    app.landlock_active = False
    routes = web.RouteTableDef()
    middlewares = app._define_routes(routes)
    aio_app = web.Application(client_max_size=max_size)
    setup_session(aio_app, app._encrypted_cookie_storage(False))
    extend_meshchat_middlewares(aio_app, middlewares)
    aio_app.add_routes(routes)
    return aio_app


@pytest.mark.asyncio
@pytest.mark.usefixtures("require_loopback_tcp")
async def test_translation_pack_fetch_body_is_capped(mock_app, monkeypatch):
    """fetch_translation_pack uses request.json() directly. Every other JSON route goes through read_json_limited (1 MiB). With the production client_max_size of 256 MiB this endpoint buffers ~256 MiB per request."""
    from meshchatx.src.backend.http.routes import translation as tr

    monkeypatch.setattr(tr, "fetch_catalog", AsyncMock(return_value={}))

    aio_app = _build_aio_app_with_client_max(mock_app, 256 * 1024 * 1024)
    big_body = {"pair": "xx", "pad": "A" * (1536 * 1024)}  # > 1 MiB cap

    async with TestClient(TestServer(aio_app)) as client:
        headers = await fetch_api_csrf_headers(client)

        fetch_resp = await client.post(
            "/api/v1/translation/packs/fetch",
            json=big_body,
            headers=headers,
        )
        # Control: the same body on a read_json_limited route must 413.
        control_resp = await client.patch(
            "/api/v1/config",
            json=big_body,
            headers=headers,
        )

    assert control_resp.status == 413
    assert fetch_resp.status == 413, (
        f"fetch endpoint accepted a {len(json.dumps(big_body))}-byte body "
        f"(status {fetch_resp.status}); expected the same 1 MiB cap"
    )


# ---------------------------------------------------------------------------
# 7. CoalesceBuffer drops pending payloads when a flush callback raises
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_coalesce_buffer_drops_pending_when_flush_raises():
    from meshchatx.src.backend.websocket_runtime import CoalesceBuffer

    flushed = []

    async def flush_cb(payload):
        if payload.get("type") == "announce":
            raise RuntimeError("broadcast failed")
        flushed.append(payload)

    buf = CoalesceBuffer(flush_cb, window_sec=0.01)
    buf.offer({"type": "announce", "announce": {"destination_hash": "a" * 32}})
    buf.offer({"type": "lxmf.telemetry", "destination_hash": "b" * 32})

    await asyncio.sleep(0.15)

    # The telemetry payload must still be delivered even though the announce
    # flush raised. Currently it is silently discarded with the batch.
    assert len(flushed) == 1
    assert flushed[0]["type"] == "lxmf.telemetry"
