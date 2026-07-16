# SPDX-License-Identifier: 0BSD

"""Hypothesis property/fuzz coverage for the generic RNS Link API."""

from __future__ import annotations

import asyncio
import base64
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from meshchatx.meshchat import ReticulumMeshChat
from meshchatx.src.backend import rns_link_manager as rlm
from meshchatx.src.backend.websocket_config_guard import (
    WEBSOCKET_MUTATOR_TYPES,
    websocket_type_requires_auth,
)
from tests.backend.ws_json_contract_schemas import assert_ws_message_matches_schema

st_aspect = st.text(
    alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789._-"),
    min_size=1,
    max_size=64,
).filter(lambda value: any(ch.isalnum() for ch in value))

st_hex_hash = st.binary(min_size=16, max_size=16).map(lambda b: b.hex())

st_request_id = st.text(min_size=1, max_size=64)

st_nasty_payload = st.one_of(
    st.binary(min_size=0, max_size=256),
    st.text(min_size=0, max_size=128).map(lambda s: s.encode("utf-8", errors="ignore")),
)


@pytest.fixture(autouse=True)
def clear_link_cache():
    with rlm._rns_links_lock:
        rlm.rns_cached_links.clear()
        rlm._link_failure_counts.clear()
    yield
    with rlm._rns_links_lock:
        rlm.rns_cached_links.clear()
        rlm._link_failure_counts.clear()


def _make_app():
    app = ReticulumMeshChat.__new__(ReticulumMeshChat)
    app._rns_link_tasks = {}
    app._rns_request_receipts = {}
    app.rns_link_manager = MagicMock()
    return app


def _capture_client():
    client = MagicMock()
    sent: list[dict] = []

    async def capture_send(payload: str):
        sent.append(json.loads(payload))

    client.send_str = AsyncMock(side_effect=capture_send)
    return client, sent


@given(aspect=st.text(min_size=0, max_size=80))
@settings(max_examples=80, deadline=None)
def test_split_aspect_never_crashes(aspect):
    try:
        app_name, sub = rlm._split_aspect(aspect)
    except ValueError:
        return
    assert isinstance(app_name, str) and app_name
    assert isinstance(sub, list)
    assert all(isinstance(part, str) and part for part in sub)


@given(aspect=st_aspect, dest=st.binary(min_size=16, max_size=16))
@settings(max_examples=60, deadline=None)
def test_cache_roundtrip_property(aspect, dest):
    link = MagicMock()
    link.status = rlm.RNS.Link.ACTIVE
    rlm._cache_link_if_active(aspect, dest, link)
    assert rlm.get_cached_active_link(aspect, dest) is link
    rlm._uncache_link_if_matches(aspect, dest, link)
    assert rlm.get_cached_active_link(aspect, dest) is None


@given(
    dest=st.binary(min_size=16, max_size=16),
    failures=st.integers(min_value=1, max_value=8),
)
@settings(max_examples=40, deadline=None)
def test_failure_recycle_threshold_property(dest, failures):
    key = ("app.aspect", dest)
    link = MagicMock()
    with rlm._rns_links_lock:
        rlm.rns_cached_links[key] = link
        rlm._link_failure_counts.pop(key, None)
    recycled_at = None
    for i in range(failures):
        _count, recycled = rlm._record_failure_and_maybe_recycle(key)
        if recycled:
            recycled_at = i + 1
            break
    if failures >= rlm._LINK_RECYCLE_FAILURE_THRESHOLD:
        assert recycled_at == rlm._LINK_RECYCLE_FAILURE_THRESHOLD
        assert key not in rlm.rns_cached_links
        link.teardown.assert_called()
    else:
        assert recycled_at is None
        assert key in rlm.rns_cached_links


def test_rns_link_mutators_require_auth():
    for msg_type in (
        "rns.link.open",
        "rns.link.identify",
        "rns.link.request",
        "rns.link.send",
        "rns.link.close",
    ):
        assert msg_type in WEBSOCKET_MUTATOR_TYPES
        assert websocket_type_requires_auth(msg_type) is True


@given(
    dest_hex=st.one_of(st_hex_hash, st.text(min_size=0, max_size=40), st.none()),
    aspect=st.one_of(st_aspect, st.text(min_size=0, max_size=40), st.none()),
    request_id=st_request_id,
)
@settings(max_examples=50, deadline=None)
def test_rns_link_open_parse_failures_never_raise(dest_hex, aspect, request_id):
    async def _run():
        app = _make_app()
        app.rns_link_manager.open_link = AsyncMock(
            return_value=(MagicMock(), False, None),
        )
        client, sent = _capture_client()
        await app._handle_rns_link_open(
            client,
            {
                "destination_hash": dest_hex,
                "aspect": aspect,
                "request_id": request_id,
            },
        )
        assert sent
        for payload in sent:
            assert payload["type"] == "rns.link.open"
            assert_ws_message_matches_schema(payload)

    asyncio.run(_run())


@given(
    dest_hex=st_hex_hash,
    aspect=st_aspect,
    payload=st_nasty_payload,
    request_id=st.text(min_size=1, max_size=24),
)
@settings(max_examples=40, deadline=None)
def test_rns_link_send_fuzz_never_raises(dest_hex, aspect, payload, request_id):
    async def _run():
        app = _make_app()
        app.rns_link_manager.send_packet = MagicMock(return_value=(True, None))
        client, sent = _capture_client()
        await app._handle_rns_link_send(
            client,
            {
                "destination_hash": dest_hex,
                "aspect": aspect,
                "request_id": request_id,
                "payload_b64": base64.b64encode(payload).decode("ascii"),
            },
        )
        assert sent
        assert sent[-1]["type"] == "rns.link.send"
        assert_ws_message_matches_schema(sent[-1])

    asyncio.run(_run())


@given(
    dest_hex=st_hex_hash,
    aspect=st_aspect,
    path=st.one_of(st.text(min_size=0, max_size=64), st.none()),
    data_b64=st.one_of(
        st.none(),
        st.just(""),
        st.just("!!!not-base64!!!"),
        st.just("%%%%"),
        st.binary(min_size=0, max_size=64).map(
            lambda b: base64.b64encode(b).decode("ascii"),
        ),
    ),
    request_id=st.text(min_size=1, max_size=24),
)
@settings(max_examples=40, deadline=None)
def test_rns_link_request_fuzz_never_raises(
    dest_hex,
    aspect,
    path,
    data_b64,
    request_id,
):
    async def _run():
        app = _make_app()
        app.rns_link_manager.open_link = AsyncMock(
            return_value=(None, False, "no_path_to_destination"),
        )
        client, sent = _capture_client()
        await app._handle_rns_link_request(
            client,
            {
                "destination_hash": dest_hex,
                "aspect": aspect,
                "path": path,
                "data_b64": data_b64,
                "request_id": request_id,
            },
        )
        assert sent
        for payload in sent:
            assert payload["type"] == "rns.link.request"
            assert_ws_message_matches_schema(payload)

    asyncio.run(_run())


@pytest.mark.asyncio
async def test_rns_link_open_success_contract():
    app = _make_app()
    app.rns_link_manager.open_link = AsyncMock(return_value=(MagicMock(), True, None))
    client, sent = _capture_client()
    await app._handle_rns_link_open(
        client,
        {
            "destination_hash": "aa" * 16,
            "aspect": "microrn.mgmt",
            "request_id": "req-open",
            "auto_identify": True,
        },
    )
    success = [p for p in sent if p.get("status") == "success"]
    assert success
    assert_ws_message_matches_schema(success[-1])
    assert success[-1]["identified"] is True


@pytest.mark.asyncio
async def test_rns_link_close_and_identify_contracts():
    app = _make_app()
    app.rns_link_manager.identify = MagicMock(return_value=(True, None))
    app.rns_link_manager.close = MagicMock(return_value=True)
    client, sent = _capture_client()
    await app._handle_rns_link_identify(
        client,
        {
            "destination_hash": "bb" * 16,
            "aspect": "microrn.mgmt",
            "request_id": "req-id",
        },
    )
    await app._handle_rns_link_close(
        client,
        {
            "destination_hash": "bb" * 16,
            "aspect": "microrn.mgmt",
            "request_id": "req-close",
        },
    )
    assert {p["type"] for p in sent} == {"rns.link.identify", "rns.link.close"}
    for payload in sent:
        assert_ws_message_matches_schema(payload)
        assert payload["status"] == "success"


@pytest.mark.asyncio
async def test_rns_link_invalid_payload_b64():
    app = _make_app()
    client, sent = _capture_client()
    await app._handle_rns_link_send(
        client,
        {
            "destination_hash": "aa" * 16,
            "aspect": "microrn.mgmt",
            "request_id": "bad-b64",
            "payload_b64": "%%%",
        },
    )
    assert sent[-1]["status"] == "failure"
    assert sent[-1]["failure_reason"] == "invalid_payload_b64"


@pytest.mark.asyncio
async def test_rns_link_request_missing_path():
    app = _make_app()
    client, sent = _capture_client()
    await app._handle_rns_link_request(
        client,
        {
            "destination_hash": "aa" * 16,
            "aspect": "microrn.mgmt",
            "request_id": "no-path",
        },
    )
    assert sent[-1]["status"] == "failure"
    assert sent[-1]["failure_reason"] == "missing_path"


def _run_async_immediate(coro):
    return asyncio.create_task(coro)


@pytest.mark.asyncio
async def test_rns_link_mutator_rejected_without_auth(mock_app):
    mock_app.config.auth_enabled.set(True)
    mock_app.config.auth_password_hash.set("hash")
    client = MagicMock()
    client.request = MagicMock()
    client.send_str = AsyncMock()

    with (
        patch.object(mock_app, "_websocket_session_authorized", return_value=False),
        patch(
            "meshchatx.meshchat.AsyncUtils.run_async",
            side_effect=_run_async_immediate,
        ),
    ):
        await mock_app.on_websocket_data_received(
            client,
            {
                "type": "rns.link.open",
                "destination_hash": "aa" * 16,
                "aspect": "microrn.mgmt",
                "request_id": "auth-denied",
            },
        )
        await asyncio.sleep(0)

    client.send_str.assert_awaited()
    payload = client.send_str.await_args.args[0]
    assert "Authentication required" in payload


@given(
    event=st.sampled_from(["packet_received", "link_closed"]),
    dest=st_hex_hash,
    aspect=st_aspect,
    payload=st.one_of(st.none(), st.binary(min_size=0, max_size=32)),
)
@settings(max_examples=40, deadline=None)
def test_rns_link_event_schema_property(event, dest, aspect, payload):
    message = {
        "type": "rns.link.event",
        "event": event,
        "destination_hash": dest,
        "aspect": aspect,
    }
    if payload is not None:
        message["payload_b64"] = base64.b64encode(payload).decode("ascii")
    assert_ws_message_matches_schema(message)
