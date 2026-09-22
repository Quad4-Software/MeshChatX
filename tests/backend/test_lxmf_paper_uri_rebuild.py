# SPDX-License-Identifier: 0BSD

"""Rebuild paper URIs for stored outbound LXMF messages (DB fallback)."""

from __future__ import annotations

import base64
import json
from types import SimpleNamespace

import LXMF
import pytest
import RNS
import RNS.vendor.umsgpack as msgpack
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from meshchatx.src.backend.http.routes.lxmf import register_lxmf_routes
from meshchatx.src.backend.lxmf_utils import (
    convert_lxmf_message_to_dict,
    lxmf_wire_fields_from_stored,
    parse_stored_lxmf_fields,
    rebuild_paper_uri_from_db_lxmf_message,
)


def _destinations():
    src_identity = RNS.Identity()
    dst_identity = RNS.Identity()
    src = RNS.Destination(
        src_identity,
        RNS.Destination.OUT,
        RNS.Destination.SINGLE,
        "lxmf",
        "delivery",
    )
    # OUT avoids Transport registration, which needs a running Reticulum.
    # Direction does not affect the destination hash or encryption.
    dst = RNS.Destination(
        dst_identity,
        RNS.Destination.OUT,
        RNS.Destination.SINGLE,
        "lxmf",
        "delivery",
    )
    return src_identity, dst_identity, src, dst


def _stored_row(lxm) -> dict:
    row = convert_lxmf_message_to_dict(lxm, include_attachments=True)
    row["is_incoming"] = 0
    row["fields"] = json.dumps(row["fields"])
    row.setdefault("reply_to_hash", None)
    return row


def _app_for(src, dst_identity, monkeypatch):
    monkeypatch.setattr(
        RNS.Identity,
        "recall",
        staticmethod(lambda *a, **k: dst_identity),
    )
    return SimpleNamespace(
        database=SimpleNamespace(
            announces=SimpleNamespace(get_announce_by_hash=lambda h: None),
        ),
        local_lxmf_destination=src,
    )


def _decode_paper_uri(uri: str):
    payload = uri.split("://", 1)[1]
    packed = base64.urlsafe_b64decode(payload + "==")
    dest_len = LXMF.LXMessage.DESTINATION_LENGTH
    return packed[:dest_len], packed[dest_len:]


def test_rebuild_paper_uri_roundtrip(monkeypatch):
    _src_identity, dst_identity, src, dst = _destinations()
    lxm = LXMF.LXMessage(
        dst,
        src,
        "hello paper world",
        title="greeting",
        desired_method=LXMF.LXMessage.DIRECT,
    )
    lxm.fields = {LXMF.FIELD_RENDERER: LXMF.RENDERER_MARKDOWN}
    lxm.pack()
    row = _stored_row(lxm)

    app = _app_for(src, dst_identity, monkeypatch)
    uri, err = rebuild_paper_uri_from_db_lxmf_message(app, row)
    assert err is None
    assert uri.startswith("lxm://")

    dest_hash, encrypted = _decode_paper_uri(uri)
    assert dest_hash == dst.hash
    decrypted = dst_identity.decrypt(encrypted)
    src_len = LXMF.LXMessage.DESTINATION_LENGTH
    sig_len = LXMF.LXMessage.SIGNATURE_LENGTH
    source_hash = decrypted[:src_len]
    packed_payload = decrypted[src_len + sig_len :]
    assert source_hash == src.hash
    payload = msgpack.unpackb(packed_payload)
    assert payload[0] == lxm.timestamp
    content = payload[2]
    assert (
        content == "hello paper world"
        or content == b"hello paper world"
    )
    # Same timestamp and payload keep the original message hash so ingest
    # dedupes instead of duplicating.
    hashed_part = dest_hash + source_hash + packed_payload
    assert RNS.Identity.full_hash(hashed_part) == lxm.hash


def test_rebuild_paper_uri_preserves_image_field(monkeypatch):
    _src_identity, dst_identity, src, dst = _destinations()
    image_bytes = b"\x89PNG\r\n\x1a\nfakepngdata"
    lxm = LXMF.LXMessage(
        dst,
        src,
        "with image",
        title="",
        desired_method=LXMF.LXMessage.DIRECT,
    )
    lxm.fields = {
        LXMF.FIELD_RENDERER: LXMF.RENDERER_MARKDOWN,
        LXMF.FIELD_IMAGE: ["png", image_bytes],
    }
    lxm.pack()
    row = _stored_row(lxm)

    fields = parse_stored_lxmf_fields(row["fields"])
    wire = lxmf_wire_fields_from_stored(fields, row)
    assert wire[LXMF.FIELD_IMAGE] == ["png", image_bytes]
    assert wire[LXMF.FIELD_RENDERER] == LXMF.RENDERER_MARKDOWN

    app = _app_for(src, dst_identity, monkeypatch)
    uri, err = rebuild_paper_uri_from_db_lxmf_message(app, row)
    assert err is None
    assert uri.startswith("lxm://")


def test_rebuild_paper_uri_rejects_incoming(monkeypatch):
    _src_identity, dst_identity, src, dst = _destinations()
    lxm = LXMF.LXMessage(
        dst,
        src,
        "inbound copy",
        title="",
        desired_method=LXMF.LXMessage.DIRECT,
    )
    lxm.fields = {}
    lxm.pack()
    row = _stored_row(lxm)
    row["is_incoming"] = 1
    # Inbound rows swap source/destination meaning; keep the stored hashes.
    row["source_hash"], row["destination_hash"] = (
        row["destination_hash"],
        row["source_hash"],
    )

    app = _app_for(src, dst_identity, monkeypatch)
    uri, err = rebuild_paper_uri_from_db_lxmf_message(app, row)
    assert uri is None
    assert "sent" in err


def test_rebuild_paper_uri_rejects_unknown_identity(monkeypatch):
    _src_identity, _dst_identity, src, dst = _destinations()
    lxm = LXMF.LXMessage(
        dst,
        src,
        "no identity",
        title="",
        desired_method=LXMF.LXMessage.DIRECT,
    )
    lxm.fields = {}
    lxm.pack()
    row = _stored_row(lxm)

    monkeypatch.setattr(
        RNS.Identity,
        "recall",
        staticmethod(lambda *a, **k: None),
    )
    app = SimpleNamespace(
        database=SimpleNamespace(
            announces=SimpleNamespace(get_announce_by_hash=lambda h: None),
        ),
        local_lxmf_destination=src,
    )
    uri, err = rebuild_paper_uri_from_db_lxmf_message(app, row)
    assert uri is None
    assert "identity" in err.lower()


def test_rebuild_paper_uri_recovers_identity_from_announces(monkeypatch):
    _src_identity, dst_identity, src, dst = _destinations()
    lxm = LXMF.LXMessage(
        dst,
        src,
        "announce fallback",
        title="",
        desired_method=LXMF.LXMessage.DIRECT,
    )
    lxm.fields = {}
    lxm.pack()
    row = _stored_row(lxm)

    announce_row = {
        "identity_public_key": base64.b64encode(
            dst_identity.get_public_key(),
        ).decode("utf-8"),
    }
    # RNS.Identity.recall finds nothing; the announces table has the key.
    monkeypatch.setattr(
        RNS.Identity,
        "recall",
        staticmethod(lambda *a, **k: None),
    )
    app = SimpleNamespace(
        database=SimpleNamespace(
            announces=SimpleNamespace(
                get_announce_by_hash=lambda h: announce_row,
            ),
        ),
        local_lxmf_destination=src,
    )
    uri, err = rebuild_paper_uri_from_db_lxmf_message(app, row)
    assert err is None
    assert uri.startswith("lxm://")


def _route_app(src, dst_identity, row, monkeypatch):
    monkeypatch.setattr(
        RNS.Identity,
        "recall",
        staticmethod(lambda *a, **k: dst_identity),
    )
    return SimpleNamespace(
        database=SimpleNamespace(
            announces=SimpleNamespace(get_announce_by_hash=lambda h: None),
            messages=SimpleNamespace(
                get_lxmf_message_by_hash=lambda h: row
                if h == row["hash"]
                else None,
            ),
        ),
        local_lxmf_destination=src,
        message_router=SimpleNamespace(
            pending_outbound=[],
            pending_deferred_stamps={},
        ),
    )


async def _get_uri_status(app, message_hash: str):
    routes = web.RouteTableDef()
    register_lxmf_routes(routes, app)
    aio = web.Application()
    aio.add_routes(routes)
    async with TestClient(TestServer(aio)) as client:
        resp = await client.get(f"/api/v1/lxmf-messages/{message_hash}/uri")
        try:
            body = await resp.json()
        except Exception:
            body = {}
        return resp.status, body


def _packed_outbound_row():
    _src_identity, dst_identity, src, dst = _destinations()
    lxm = LXMF.LXMessage(
        dst,
        src,
        "route level paper",
        title="",
        desired_method=LXMF.LXMessage.DIRECT,
    )
    lxm.fields = {LXMF.FIELD_RENDERER: LXMF.RENDERER_MARKDOWN}
    lxm.pack()
    return src, dst_identity, _stored_row(lxm)


@pytest.mark.asyncio
async def test_uri_route_rebuilds_outbound_from_db(monkeypatch):
    src, dst_identity, row = _packed_outbound_row()
    app = _route_app(src, dst_identity, row, monkeypatch)
    status, body = await _get_uri_status(app, row["hash"])
    assert status == 200
    assert body["uri"].startswith("lxm://")


@pytest.mark.asyncio
async def test_uri_route_rejects_incoming(monkeypatch):
    src, dst_identity, row = _packed_outbound_row()
    row["is_incoming"] = 1
    app = _route_app(src, dst_identity, row, monkeypatch)
    status, body = await _get_uri_status(app, row["hash"])
    assert status == 422
    assert "message" in body


@pytest.mark.asyncio
async def test_uri_route_404s_unknown_message(monkeypatch):
    src, dst_identity, row = _packed_outbound_row()
    app = _route_app(src, dst_identity, row, monkeypatch)
    status, _body = await _get_uri_status(app, "ff" * 32)
    assert status == 404
